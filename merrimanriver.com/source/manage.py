#!/usr/bin/python3

import os, sys

sys.path.append('/home/merriman')
sys.path.append('/home/merriman/merrimanriver.com')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)