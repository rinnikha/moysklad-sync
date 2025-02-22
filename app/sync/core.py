import logging
from datetime import datetime

from sqlalchemy import exists
from app import db
from app.models import SyncLog, CounterpartyMapping, SyncLogStatus
from .client import MoySkladClient

from flask import current_app, app

from app import config

date_ms_format = "%Y-%m-%d %H:%M:%S.%f"

logger = logging.getLogger(__name__)



def perform_sync(cp_mapping: CounterpartyMapping, order_id, moment=None) -> SyncLog:
    log = SyncLog()
    try:
        positions = current_app.ms1_client.get_order_positions(order_id)
    except Exception as e:
        error_msg = f"Неудалось загрузитить товары заказа: {str(e)}"
        logger.error(f"Заказ: {order_id}: {error_msg}")

    missing_skus = []
    position_mappings = []

    for position in positions:
        # if position['assortment']['meta']['type'] != 'product':
        #         logger.warning(f"Пропуск не товарных позиций: {position['id']}")
        #         missing_skus.append(f"Найден комплект с ID: {position['id']}")
        #         continue

        is_bundle = position['assortment']['meta']['type'] == 'bundle'
        
        product_id = position['assortment']['meta']['href'].split('/')[-1]
        sku = current_app.ms1_client.get_product_sku(product_id, is_bundle)

        if not sku:
            missing_skus.append(f"Товар {position['name']} не имеет артикула в МС1")
            continue

        ms2_product_meta = current_app.ms2_client.find_product_meta_by_sku(sku, is_bundle)

        if ms2_product_meta is None:
            missing_skus.append(f"Товар с Артикулом: {sku} не найден в МС2")
            continue

        if ms2_product_meta:
            position_mappings.append({
                'quantity': position['quantity'],
                'price': position['price'],
                'ms2_product_meta': ms2_product_meta
            })

    mapped_order = {
        "agent": { "meta": cp_mapping.ms2_org_meta },
        "moment": moment,
        "applicable": True,
        "vatEnabled": False,
        "vatIncluded": False,
        "organization": { "meta": cp_mapping.ms2_org_meta},
        "group": { "meta": cp_mapping.group_meta },
        "owner": { "meta": cp_mapping.owner_meta },
        "store": { "meta": cp_mapping.store_meta },
        "description": f"Синхронизировано с помощью ARMED MS Sync. ID Заказа: {order_id}",
        "positions": [{
            "quantity": pos["quantity"],
            "price": pos['price'],
            "assortment": {"meta": pos['ms2_product_meta']}
        } for pos in position_mappings]
    }

    if moment:
        mapped_order['moment'] = moment

    # Create order in MS2
    if len(missing_skus) > 0:
        log.status = SyncLogStatus.FAILED
        log.ms2_purchase_id = None
        log.message = "\n".join(missing_skus)

        return log

    
    result = current_app.ms2_client.create_purchase_order(mapped_order)


    if result['success']:
        log.status = SyncLogStatus.COMPLETED
        log.ms2_purchase_id = result['purchase']['id']
        log.message = ''

        logger.info(f"Synced order {order_id} -> {result['purchase']['id']}")
    else:
        log.status = SyncLogStatus.FAILED
        log.ms2_purchase_id = None
        log.message = result['error_msg']

    return log

def sync_orders():
    counterparty_ids = [row[0] for row in CounterpartyMapping.query.with_entities(CounterpartyMapping.ms1_cp_id).all()]
    filter_state = current_app.config['ORDER_STATE_IDS']
    start_date = current_app.config['START_SYNC_DATE']

    orders = current_app.ms1_client.get_orders(counterparty_ids, filter_state, start_date)

    try:
        for order in orders:
            if db.session.query(exists().where(SyncLog.order_id == order['id'])).scalar():
                continue
            
            agent_id = order['agent']['meta']['href'].split('/')[-1]
            cp_mapping = CounterpartyMapping.query.filter_by(ms1_cp_id = agent_id).first()
            
            sync_log = perform_sync(cp_mapping, order['id'], order['moment'])

            sync_log.counterparty_id = cp_mapping.id
            sync_log.order_id = order['id']
            sync_log.order_moment = datetime.strptime(order['moment'], date_ms_format)
            sync_log.order_amount = order['sum']/100

            db.session.add(sync_log)
            db.session.commit()
        
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")


def retry_order_sync(sync_log_id):
    try:
        # Get existing log
        log = SyncLog.query.get(sync_log_id)
        
        if not log:
            raise ValueError(f"No log found with id {sync_log_id}")
            
        # Attempt sync
        result = perform_sync(log.counterparty, log.order_id)
        
        # Update log
        update_sync_log(
            sync_log_id,
            result
        )
        
        return result
        
    except Exception as e:
        # Update log with error
        error_log = SyncLog()
        error_log.status = SyncLogStatus.FAILED
        error_log.message = str(e)
        
        if log:
            update_sync_log(
                log.id,
                error_log
            )
        raise

def update_sync_log(log_id, updated_log: SyncLog):
    """
    Update an existing sync log entry
    
    Args:
        log_id (int): ID of the log to update
        status (str): New status ('success' or 'error')
        message (str): Optional message update
        details (str): Optional details update
    """
    try:
        # Find the log entry
        log = SyncLog.query.get(log_id)
        
        if not log:
            raise ValueError(f"Log with ID {log_id} not found")
        
        # Update fields
        log.status = updated_log.status
        log.sync_time = datetime.utcnow()
        
        if updated_log.message:
            log.message = updated_log.message
            
        if updated_log.details:
            log.details = updated_log.details
            
        # Commit changes
        db.session.commit()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating log {log_id}: {str(e)}")
        return False