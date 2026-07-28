from .sepehr import SepehrGateway
from .sizpay import SizPayGateway
from ..models import PaymentGateway

_GATEWAYS = {
    PaymentGateway.SIZPAY: SizPayGateway,
    PaymentGateway.SEPEHR: SepehrGateway,
}


class PaymentGatewayFactory:
    @staticmethod
    def get_gateway(gateway):
        gateway_cls = _GATEWAYS.get(gateway)
        if gateway_cls is None:
            raise ValueError("درگاه پرداخت پشتیبانی نمیشود")
        return gateway_cls()
