# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import tools

from mongo import *
from subheaven.arg_parser import *

class SQLiter(object):
    def __init__(self, dbname, dbfolder = ''):
        self.dbname = dbname
        self.mappedTables = {}
        if dbfolder == '':
            self.datapath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sqliter', 'data')
            self.schemapath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sqliter', 'schema')
        else:
            self.datapath = os.path.join(dbfolder, 'sqliter', 'data')
            self.schemapath = os.path.join(dbfolder, 'sqliter', 'schema')
        self.mapDef = self.__mountMapDefinition()
        self.insertMap = self.__mountInsertMap()
        tools.CheckFolder(self.datapath)
        tools.CheckFolder(self.schemapath)
        self.datapath = os.path.join(self.datapath, f"{self.dbname}.db")
        self.db_created = os.path.exists(self.datapath)
        self.conn = sqlite3.connect(self.datapath)

    def __saveSchema(self, name, schema):
        with codecs.open(os.path.join(self.schemapath, f'{name}.json'), 'w', 'utf8') as file:
            file.write(json.dumps(schema, indent=4))

    def __insertInteger(self, value):
        return str(value)

    def __insertText(self, value):
        v = '<asp>'.join(value.split("'"))
        return f"'{v}'"

    def __insertJson(self, value):
        #sjson = "<aps>".join(json.dumps(value).split("'"))
        package = "<aps>".join(json.dumps(value).split("'"))
        return f"'{package}'"

    def __insertDatetime(self, value):
        return f"'{str(value)}'"

    def __insertBoolean(self, value):
        return "1" if value else "0"

    def __mountInsertMap(self):
        return {
            'integer': self.__insertInteger,
            'text': self.__insertText,
            'json': self.__insertJson,
            'datetime': self.__insertDatetime,
            'boolean': self.__insertBoolean
        }

    def __mountMapDefinition(self):
        return {
            "integer": self.__integerDef,
            "text": self.__textDef,
            "json": self.__jsonDef,
            "datetime": self.__datetimetDef,
            "boolean": self.__booleanDef
        }

    def __integerDef(self, name, definition):
        sql = f"{name} INTEGER"
        if 'notnull' in definition and definition['notnull']:
            sql += ' NOT NULL'
        if 'default' in definition and definition['default'] != None:
            sql += f" DEFAULT {definition['default']}"
        return sql

    def __textDef(self, name, definition):
        sql = f"{name} TEXT"
        if 'notnull' in definition and definition['notnull']:
            sql += ' NOT NULL'
        if 'default' in definition and definition['default'] != None:
            sql += f" DEFAULT '{definition['default']}'"
        return sql

    def __jsonDef(self, name, definition):
        sql = f"{name} CLOB"
        if 'notnull' in definition and definition['notnull']:
            sql += ' NOT NULL'
        if 'default' in definition and definition['default'] != None:
            sql += f" DEFAULT '{definition['default']}'"
        return sql

    def __datetimetDef(self, name, definition):
        sql = f"{name} DATETIME"
        if 'notnull' in definition and definition['notnull']:
            sql += ' NOT NULL'
        if 'default' in definition and definition['default'] != None:
            sql += f" DEFAULT DATETIME('{definition['default']}')"
        return sql

    def __booleanDef(self, name, definition):
        sql = f"{name} BOOLEAN"
        if 'notnull' in definition and definition['notnull']:
            sql += ' NOT NULL'
        if 'default' in definition and definition['default'] != None:
            if definition['default']:
                sql += f" DEFAULT 1"
            else:
                sql += f" DEFAULT 0"
        return sql

    def __createTable(self, name, schema):
        sql = f"CREATE TABLE {name} ("
        sql += "\n    id integer primary key autoincrement not null"
        for k in schema:
            sql += f",\n    {self.mapDef[schema[k]['type']](k, schema[k])}"
        sql += f"\n);"
        self.execute(sql)
        self.__saveSchema(name, schema)

    def __mapTables(self):
        dataset = {}
        for table in self.select("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
            dataset[table['name']] = {}
            for field in self.select(f"SELECT m.name AS tableName, p.* FROM sqlite_master m LEFT OUTER JOIN pragma_table_info((m.name)) p ON m.name <> p.name WHERE m.name = '{table['name']}' ORDER BY tableName, p.cid"):
                if field['name'] != 'id':
                    ftype = field['type'].lower()
                    dataset[table['name']][field['name']] = {
                        'type': 'json' if ftype == 'clob' else ftype
                    }
                    if field['notnull'] == 1:
                        dataset[table['name']][field['name']]['notnull'] = True
                    if field['dflt_value'] != None:
                        if dataset[table['name']][field['name']]['type'] == 'boolean':
                            dataset[table['name']][field['name']]['default'] = field['dflt_value'] == "1"
                        else:
                            dataset[table['name']][field['name']]['default'] = field['dflt_value']
        return dataset
    
    def __createIndex(self, name, schema):
        for field in schema:
            if "index" in schema[field] and schema[field]['index']:
                sql = f"CREATE INDEX {name}_{field}_index ON {name} ({field})"
                self.execute(sql)

    def checkTable(self, name, schema):
        self.mappedTables = self.__mapTables()
        if not name in self.mappedTables:
            self.__createTable(name, schema)
            self.__createIndex(name, schema)
            self.mappedTables[name] = schema

    def select(self, sql):
        tablename = sql.strip().lower().split('from ')[1].split(' ')[0].strip()
        tableschema = None
        if tablename in self.mappedTables:
            tableschema = self.mappedTables[tablename]
        dataset = []
        with sqlite3.connect(self.datapath) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql.strip())
            row = cursor.fetchone()
            if row != None:
                keys = row.keys()
                while row != None:
                    data = {}
                    for i in range(len(keys)):
                        if tableschema != None and keys[i] != "id" and tableschema[keys[i]]['type'] == 'json':
                            package = "'".join(tuple(row)[i].split('<aps>'))
                            data[keys[i]] = json.loads(package)
                        elif tableschema != None and keys[i] != "id" and tableschema[keys[i]]['type'] == 'text':
                            data[keys[i]] = "'".join(tuple(row)[i].split('<aps>'))
                        elif tableschema != None and keys[i] != "id" and tableschema[keys[i]]['type'] == 'boolean':
                            data[keys[i]] = tuple(row)[i] == 1
                        else:
                            data[keys[i]] = tuple(row)[i]
                    dataset.append(data)
                    row = cursor.fetchone()
        return dataset

    def execute(self, sql):
        with sqlite3.connect(self.datapath) as conn:
            conn.execute(sql.strip())
        return True

    def insert_one(self, tablename, data):
        if tablename in self.mappedTables:
            sql = f"INSERT INTO {tablename} ("
            comma = ""
            for field in data:
                if field in self.mappedTables[tablename]:
                    sql += f"{comma}\n    {field}"
                    comma = ","
                else:
                    tools.log(f"Campo inválido. Campo {field} nao existe na tabela {tablename}.")
            sql += f"\n) VALUES ("
            comma = ""

            for field in data:
                if field in self.mappedTables[tablename]:
                    sql += f"{comma}\n    {self.insertMap[self.mappedTables[tablename][field]['type']](data[field])}"
                    comma = ","
            sql += "\n)"
            self.execute(sql)
            return True
        return False

    def update_one(self, tablename, query, data):
        sql = f"UPDATE {tablename} SET"
        comma = ""
        for field in data:
            if field != 'id':
                sql += f"{comma}\n    {field} = {self.insertMap[self.mappedTables[tablename][field]['type']](data[field])}"
                comma = ","

        sql += "\nWHERE"
        comma = ""
        for field in query:
            if field == 'id':
                sql += f"\n  {comma} id = {query['id']}"
            else:
                sql += f"\n  {comma} {field} = {self.insertMap[self.mappedTables[tablename][field]['type']](query[field])}"
            comma = "AND"

        self.execute(sql)

if __name__ == "__main__":
    @arg_parser(".".join(os.path.basename(__file__).split(".")[0:-1]), 'Teste para analisar o sequencial de notas de uma empresa')
    # @positional_param('salute', 'Tipo de saudação.', sample='Bom dia', required=False, options=['Bom dia', 'Boa tarde', 'Boa noite'])
    # @positional_param('nome', 'Nome de quem será cumprimentado.', required=False, sample='mundo')
    @named_param('empresa', 'Código da empresa.', sample='1387', required=False)
    # @named_param('competencia', 'Indica a competência a ser processada. Se não for informada, processa a competência atual.', sample='202112', required=False)
    # @named_param('anoini', 'Ano inicial. Se não for informado, processa o ano atual.', sample='2020', required=False)
    # @boolean_param('debug', 'Mostra apenas os dados de calculo de sequencial')
    def processar():
        #parseParams()
        sqliter = SQLiter('sqliter')
        sqliter.checkTable("teste", {
            "empresa": {
                "type": "text",
                "default": ""
            },
            "tipo": {
                "type": "text",
                "default": ""
            },
            "arquivo": {
                "type": "json",
                "notnull": True
            },
            "md5": {
                "type": "text",
                "default": ""
            },
            "data_envio": {
                "type": "datetime",
                "index": True
            }
        })
        tools.exit()
    processar()