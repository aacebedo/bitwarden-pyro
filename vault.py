#!/usr/bin/env python

from subprocess import CalledProcessError
from logger import BwLogger
import subprocess as sp
import json


class Vault:
    def __init__(self):
        self._items = None

        self._logger = BwLogger().get_logger()

    def load_items(self, key):
        try:
            self._logger.info("Loading items from bw")
            load_cmd = f"bw list items --session {key}"

            proc = sp.run(load_cmd.split(), capture_output=True, check=True)
            items_json = proc.stdout.decode("utf-8")
            self._items = json.loads(items_json)

            return len(self._items)
        except CalledProcessError:
            self._logger.error("Failed to load vault items")
            return 0

    def get_items(self):
        return self._items

    def get_by_name(self, name):
        return [i for i in self._items if i['name'] == name]


class VaultFormatter:
    DEDUP_MARKER = '+ '

    @staticmethod
    def unique_format(items):
        unique = {}
        for item in items:
            arr = unique.get(item['name'], [])
            arr.append(item)
            unique[item['name']] = arr

        strings = []
        for name, arr in unique.items():
            if len(arr) == 1:
                strings.append(name)
            else:
                strings.append(
                    f"{VaultFormatter.DEDUP_MARKER}{name}")

        return "\n".join(strings)


class VaultException(Exception):
    """Base class for items generated by Vault"""
    pass


class LoadException(VaultException):
    """Raised when vault fails to load items"""
    pass
