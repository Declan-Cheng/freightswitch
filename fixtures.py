"""New synthetic messages; no real people, warehouse or carrier records."""
import copy
import hashlib

SHIPMENT='FS-1042'
PARTIES={'customer':'Maya Chen · Customer','dispatcher':'Alex Morgan · Dispatcher','driver':'Sam Rivera · Driver'}
OLD={'address':'14 Cedar Lane, Warehouse A, Gate 1','time':'2026-10-27T09:00:00-04:00'}
NEW={'address':'88 Birch Avenue, Warehouse B, Gate 4','time':'2026-10-27T11:30:00-04:00'}
LATE={'address':NEW['address'],'time':'2026-10-27T13:00:00-04:00'}


def message(ident,kind,party,minute,version=None,details=None,ref=None,body=None,**extra):
    at='2026-10-27T08:%02d:00-04:00'%minute
    target='shipment '+SHIPMENT+(' / '+version if version else '')
    if body is None:
        verbs={'propose':'I propose','accept':'I explicitly accept','received':'I received, but have NOT accepted','reject':'I reject','withdraw':'I withdraw'}
        body=verbs[kind]+' '+target+('. Request '+ref if ref else '')+'.'
        if details:body+=' Deliver to '+details['address']+' at '+details['time']+'.'
        if extra.get('supersedes'):body+=' This supersedes message '+extra['supersedes']+'.'
    result=dict(id=ident,shipment=SHIPMENT,kind=kind,party=party,identityVerified=True,sentAt=at,version=version,ref=ref,details=copy.deepcopy(details),body=body,sha256=hashlib.sha256(body.encode()).hexdigest(),synthetic=True,**extra)
    return result


def events():
    return [
        message('m01','propose','customer',0,'v1',OLD,body='I propose shipment FS-1042 / v1. Deliver to '+OLD['address']+' at '+OLD['time']+'.'),
        message('m02','accept','customer',1,'v1',OLD,'m01'),
        message('m03','accept','dispatcher',2,'v1',OLD,'m01'),
        message('m04','accept','driver',3,'v1',OLD,'m01'),
        message('m05','propose','customer',10,'v2',NEW),
        message('m06','accept','customer',11,'v2',NEW,'m05'),
        message('m07','received','dispatcher',12,'v2',ref='m05'),
        message('m08','accept','driver',13,'v1',OLD,'m01'),
        message('m09','accept','dispatcher',14,'v2',NEW,'m05'),
        message('m10','received','driver',15,'v2',ref='m05'),
        message('m11','accept','driver',16,'v2',NEW,'m05'),
        message('m12','propose','customer',20,'v3',LATE),
        message('m13','accept','customer',21,'v3',LATE,'m12'),
        message('m14','withdraw','customer',22,'v3',ref='m12'),
        message('m15','accept','driver',23,'v3',LATE,'m12'),
    ]

SCENES=[dict(id='agreement',label='01 · Original agreement',count=4,caption='Three explicit confirmations establish Warehouse A at 09:00.'),
        dict(id='risk',label='02 · Change creates risk',count=8,caption='The customer changes warehouse and time. The driver still confirms v1; received is not accepted.'),
        dict(id='received',label='03 · Received ≠ accepted',count=10,caption='Dispatch accepts v2. The driver has received it but has not accepted the new instruction.'),
        dict(id='resolved',label='04 · Explicit confirmation',count=11,caption='Risk clears only when all three explicitly confirm the exact v2 address and time.'),
        dict(id='withdrawn',label='05 · Withdrawn request',count=15,caption='A later time request is withdrawn. A driver acknowledgment of that revoked request cannot revive it.')]


def recovery_events():
    """Review repair proof: a new complete instruction resolves older warnings."""
    return events()+[
        message('r16','propose','customer',24,'v4',LATE),
        message('r17','accept','customer',25,'v4',LATE,'r16'),
        message('r18','accept','dispatcher',26,'v4',LATE,'r16'),
        message('r19','accept','driver',27,'v4',LATE,'r16'),
    ]

RECOVERY_SCENE=dict(id='recovered',label='06 · New agreement',count=19,caption='A new complete v4 agreement clears the old warning. Its original and resolution evidence remain in history.')
