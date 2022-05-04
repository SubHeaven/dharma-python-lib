# -*- coding: utf-8 -*-
import codecs
import datetime
import os
import sqliter
import sybase
import sys
import tools

from mongo import *
from subheaven.arg_parser import *

class Queuer(object):
    def __init__(self, queue_name):
        self.database = None
        self.name = queue_name
        self.prepareDatabase()

    def prepareDatabase(self):
        self.database = sqliter.SQLiter(self.name)
        self.database.checkTable("pending", {
            "package": {
                "type": "json",
                "notnull": True
            },
            "processing": {
                "type": "boolean",
                "default": False
            },
            "log": {
                "type": "text",
                "default": ""
            },
            "tryout": {
                "type": "integer",
                "default": 0
            },
            "queue_date": {
                "type": "datetime",
                'index': True
            },
            "add_date": {
                "type": "datetime"
            }
        })
        self.database.checkTable("history", {
            "package": {
                "type": "json",
                "notnull": True
            },
            "log": {
                "type": "text",
                "default": ""
            },
            "tryout": {
                "type": "integer",
                "default": 0
            },
            "process_date": {
                "type": "datetime",
                'index': True
            },
            "add_date": {
                "type": "datetime"
            }
        })
    
    def add(self, data):
        now = str(datetime.datetime.now()).split('.')[0]
        data = {
            "package": data,
            "queue_date": now,
            "add_date": now
        }
        self.database.insert_one('pending', data)
    
    def process(self, fn):
        pendente = self.database.select("SELECT * FROM pending WHERE processing = 0 ORDER BY queue_date LIMIT 1")
        if len(pendente) > 0:
            pendente = pendente[0]
            self.database.execute(f"UPDATE pending SET processing = 1 WHERE id = {pendente['id']}")
            try:
                result = fn(pendente['package'])
                history = {
                    "package": pendente['package'],
                    "log": str(result) if result != None else '',
                    "tryout": pendente['tryout'],
                    "process_date": str(datetime.datetime.now()).split('.')[0],
                    "add_date": pendente['add_date']
                }
                self.database.insert_one('history', history)
                self.database.execute(f"DELETE FROM pending WHERE id = {pendente['id']}")
            except Exception:
                log = '"'.join(traceback.format_exc().split("'"))
                tools.log(log)
                new_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.database.execute(f"UPDATE pending SET processing = 0, log='{log}', tryout={pendente['tryout'] + 1}, queue_date='{new_date}' WHERE id = {pendente['id']}")
            return True
        else:
            return False
    
    def processAll(self, fn):
        next = self.process(fn)
        while next:
            next = self.process(fn)

if __name__ == "__main__":
    @arg_parser(".".join(os.path.basename(__file__).split(".")[0:-1]), 'Teste para analisar o sequencial de notas de uma empresa')
    # @positional_param('salute', 'Tipo de saudação.', sample='Bom dia', required=False, options=['Bom dia', 'Boa tarde', 'Boa noite'])
    # @positional_param('nome', 'Nome de quem será cumprimentado.', required=False, sample='mundo')
    @named_param('empresa', 'Código da empresa.', sample='1387', required=False)
    # @named_param('competencia', 'Indica a competência a ser processada. Se não for informada, processa a competência atual.', sample='202112', required=False)
    # @named_param('anoini', 'Ano inicial. Se não for informado, processa o ano atual.', sample='2020', required=False)
    # @boolean_param('debug', 'Mostra apenas os dados de calculo de sequencial')
    def processar():
        queuer = Queuer('dharma-queuer')
    processar()