#!/usr/bin/env python
"""فایل مدیریتی جنگو برای پروژه قلمینو"""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "جنگو نصب نیست یا در PYTHONPATH قرار ندارد. "
            "آیا محیط مجازی را فعال کرده‌اید؟"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
