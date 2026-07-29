import logging
import requests
from django.conf import settings

logger = logging.getLogger('apps.accounts.sms')


class SMSProviderError(Exception):
    """خطای عمومی ارتباط با سرویس پیامک"""


class BaseSMSProvider:
    def send_otp(self, phone_number: str, code: str) -> bool:
        raise NotImplementedError

    def send_lookup(self, phone_number: str, template: str, token: str, token2: str = '', token3: str = '') -> bool:
        raise NotImplementedError


class ConsoleSMSProvider(BaseSMSProvider):
    def send_otp(self, phone_number: str, code: str) -> bool:
        logger.warning('[DEV OTP] کد ورود برای %s : %s', phone_number, code)
        return True

    def send_lookup(self, phone_number: str, template: str, token: str, token2: str = '', token3: str = '') -> bool:
        logger.warning(
            '[DEV SMS] الگو=%s گیرنده=%s token=%s token2=%s token3=%s',
            template, phone_number, token, token2, token3,
        )
        return True


class KavenegarSMSProvider(BaseSMSProvider):
    def __init__(self):
        self.api_key = settings.KAVENEGAR_API_KEY
        self.otp_template = settings.KAVENEGAR_OTP_TEMPLATE
        self.base_url = f'{settings.KAVENEGAR_BASE_URL}/{self.api_key}/verify/lookup.json'

    def send_otp(self, phone_number: str, code: str) -> bool:
        return self._send(phone_number, self.otp_template, code)

    def send_lookup(self, phone_number: str, template: str, token: str, token2: str = '', token3: str = '') -> bool:
        return self._send(phone_number, template, token, token2, token3)

    def _send(self, phone_number: str, template: str, token: str, token2: str = '', token3: str = '') -> bool:
        if not self.api_key:
            raise SMSProviderError('KAVENEGAR_API_KEY تنظیم نشده است.')

        params = {
            'receptor': phone_number,
            'token': token,
            'template': template,
        }
        if token2:
            params['token2'] = token2
        if token3:
            params['token3'] = token3

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SMSProviderError(f'خطا در ارتباط با سرویس پیامک: {exc}') from exc

        payload = response.json()
        return_info = payload.get('return', {})
        if return_info.get('status') != 200:
            raise SMSProviderError(return_info.get('message', 'ارسال پیامک ناموفق بود.'))
        return True


def get_sms_provider() -> BaseSMSProvider:
    backend = getattr(settings, 'SMS_BACKEND')
    if backend == 'kavenegar':
        return KavenegarSMSProvider()
    return ConsoleSMSProvider()
