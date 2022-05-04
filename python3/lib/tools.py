# -*- coding: utf-8 -*-
import bson
import base64
import codecs
import datetime
import io
import json
import operator
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import unicodedata
import xlrd
import winreg
import yaml
import tempfile
import traceback
from bson.objectid import ObjectId
import xml.etree.ElementTree as ET
import unicodedata
from contextlib import contextmanager

_internal_log = []
internal_config = None

summa_files = "C:\\inetpub\\summa\\files"

def isUserAdmin():
    if os.name == 'nt':
        import ctypes
        # WARNING: requires Windows XP SP2 or higher!
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            traceback.print_exc()
            print("Admin check failed, assuming not an admin.")
            return False
    elif os.name == 'posix':
        # Check for root on Posix
        return os.getuid() == 0
    else:
        raise RuntimeError("Unsupported operating system for this module: %s" % (os.name,))

def runAsAdmin(cmdLine=None, wait=True):
    if os.name != 'nt':
        raise RuntimeError("This function is only implemented on Windows.")

    import win32api, win32con, win32event, win32process
    from win32com.shell.shell import ShellExecuteEx
    from win32com.shell import shellcon

    python_exe = sys.executable

    if cmdLine is None:
        cmdLine = [python_exe] + sys.argv
    elif type(cmdLine) not in (types.TupleType,types.ListType):
        raise ValueError("cmdLine is not a sequence.")
    cmd = '"%s"' % (cmdLine[0],)

    params = " ".join(['"%s"' % (x,) for x in cmdLine[1:]])
    cmdDir = ''
    showCmd = win32con.SW_SHOWNORMAL
    # showCmd = win32con.SW_HIDE
    lpVerb = 'runas'

    print(" ".join(cmdLine))
    procInfo = ShellExecuteEx(nShow=showCmd,
                            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                            lpVerb=lpVerb,
                            lpFile=cmd,
                            lpParameters=params)

    if wait:
        procHandle = procInfo['hProcess']    
        obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
        rc = win32process.GetExitCodeProcess(procHandle)
    else:
        rc = None

    return rc

def conferir_privilegios():
    rc = 0
    if not isUserAdmin():
        rc = runAsAdmin()
    else:
        rc = 0
    return rc

def run_as_admin(function):
    def wrapper(*args, **kwargs):
        if conferir_privilegios() > 0:
            sys.exit(0)
        return function(*args, **kwargs)

    return wrapper

#def Log(_msg, end="{none}", flush=False):
def Log(_msg):
    try:
        _internal_log.append(str(_msg).decode("utf-8"))
        print(str(_msg).decode("utf-8"))
    except:
        _internal_log.append(str(_msg))
        print(str(_msg))

def log(_msg = ""):
    Log(_msg)

def backlog(msg = ""):
    log("\r", end="")
    log(msg, end="")

def CheckFolder(_path):
    if (not os.path.isdir(_path)):
        os.makedirs(_path)

def FileExists(filepath):
    return os.path.isfile(filepath)

def FormatFloat(s, thou=",", dec="."):
    if (isinstance(s, float)):
        s = str(round(s, 2))
    if (isinstance(s, int)):
        s = str(s)
    if len(s.split(".")) > 1:
        integer, decimal = s.split(".")
    else:
        integer, decimal = s, "0"
    integer = re.sub(r"\B(?=(?:\d{3})+$)", thou, integer)
    decimal = decimal.ljust(2, "0")
    _r = integer + dec + decimal
    _r = _r.replace(",", "|")
    _r = _r.replace(".", ",")
    _r = _r.replace("|", ".")
    return _r

# Minimaliza, ou seja, transforma todas as instancias repetidas de espaços em espaços simples.
#   Exemplo, o texto "  cnpj:      09.582.876/0001-68    Espécie Documento          Aceite" viraria
#   "cnpj: 09.582.876/0001-68 Espécie Documento Aceite"
#
# Nota: Ele faz um trim do texto também
def minimalizeSpaces(text):
    _result = text
    while ("  " in _result):
        _result = _result.replace("  ", " ")
    _result = _result.strip()
    return _result

# Retira de um texto, qualquer caracter que seja diferente da lista passada
# Exemplo clearPermittedText("CEP: 74210-122", "1234567890-")
# Resultado: "74210-122"
def clearPermittedText(text, allowed):
    _result = ""
    for ch in text:
        if ch in allowed:
            _result += ch
    return _result

def apenasNumeros(text):
    return onlyNumbers(text)

def onlyNumbers(text):
    _valid = "1234567890"
    return clearPermittedText(text, _valid)

def formatarMask(text, mask):
    _i = 0
    _result = ""
    for _m in range(len(mask)):
        if mask[_m] == "9":
            if len(text) >= _i + 1:
                _result += text[_i]
                _i += 1
            else:
                break
        elif len(text) >= _i + 1:
            _result += mask[_m]
    return _result

def formatarCPF(text):
    return formatarMask(text, "999.999.999-99")

def formatarCNPJ(text):
    return formatarMask(text, "99.999.999/9999-99")

def formatarDocumento(text):
    _result = ""
    if text == None:
        return ""
    _t = apenasNumeros(text)
    if _t == "":
        _result = ""
    if len(_t) <= 11:
        while len(_t) < 11:
            _t = "0" + _t
        _result = formatarCPF(_t)
    else:
        while len(_t) < 14:
            _t = "0" + _t
        _result = formatarCNPJ(_t)
    return _result

def RemoveAccents(text):
    _accents = "áàâãäÁÀÂÃÄéèêêÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛçÇñÑ"
    _allowed = "aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUcCnN"
    _result = ""
    for _c in text:
        if _accents.find(_c) > -1:
            _result += _allowed[_accents.find(_c)]
        else:
            _result += _c
    return _result

def LoadYAML(filepath):
    with open(filepath) as file:
        _text = file.read()
    return yaml.load(_text)

def LoadJSON(filepath):
    if (os.path.isfile(filepath)):
        with codecs.open(filepath, "r", "utf-8") as temp:
            return json.loads(temp.read())
    else:
        return None

def exit(log = "", code = 9, history=1):
    count = history
    back = -1 - history
    while count > 0:
        filename = traceback.extract_stack()[back].filename.split('\\')[-1]
        log = f"{log} " if log != "" else ""
        print("")
        print(f"{log}{filename} [{traceback.extract_stack()[back].lineno}]:")
        print("Terminando...")
        back += 1
        count -= 1
    sys.exit(code)

def stack(history=1):
    count = history
    back = -1 - history
    while count > 0:
        filename = traceback.extract_stack()[back].filename.split('\\')[-1]
        print(f"{filename} [{traceback.extract_stack()[back].lineno}]")
        back += 1
        count -= 1

def dumps(o, stack=True):
    if stack:
        print("")
        filename = traceback.extract_stack()[-2].filename.split('\\')[-1]
        print(f"{filename} [{traceback.extract_stack()[-2].lineno}]:")

    msg = json.dumps(o, default=defaultConverter, indent=4)
    print(msg)

    if stack:
        print("")
    return msg

def debug(*data, stack=True):
    if stack:
        print("")
        filename = traceback.extract_stack()[-2].filename.split('\\')[-1]
        print(f"{filename} [{traceback.extract_stack()[-2].lineno}]:")

    if isinstance(data, tuple):
        if len(data) > 1:
            for i in range(len(data)):
                debug(data[i], stack=False)
        elif len(data) == 1:
            d = data[0]
            if isinstance(d, list) or isinstance(d, dict):
                dumps(d, stack=False)
            else:
                print(d)

    if stack:
        print("")

def ReadLines(filepath):
    _lines = []
    if (FileExists(filepath)):
        if (sys.version_info[0] < 3):
            with io.open(filepath, mode="r", encoding="latin1") as f:
                _lines = f.readlines()
        else:
            if os.path.isfile(filepath):
                with open(filepath) as f:
                    _lines = f.readlines()
    return _lines

#Verificar se o cnpj e a tag informados estão na observação da empresa
def checarCNPJBase64(empresa, cnpj, tag):
    #Calcular a base 64 do cnpj e a tag
    b64 = "".join(map(chr, base64.b64encode(bytes(f"{cnpj}{tag}", 'latin1'))))
    #Se o cnpj em base 64 for encontrado na observação, retornar verdadeiro
    return b64 in empresa['obs']

def RAMUsage():
    return psutil.virtual_memory()[2]

def PCUsage():
    ram = RAMUsage()
    cpu = psutil.cpu_percent(interval=1)
    return ram, cpu

# @timeit decorator
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            log('%r  %2.2f ms'.format(method.__name__, (te - ts) * 1000))
        return result
    return timed

def removerAcentosECaracteresEspeciais(palavra):
    # Unicode normalize transforma um caracter em seu equivalente em latin.
    nfkd = unicodedata.normalize('NFKD', palavra).encode('ASCII', 'ignore').decode('ASCII')
    palavraTratada = u"".join([c for c in nfkd if not unicodedata.combining(c)])

    # Usa expressão regular para retornar a palavra apenas com valores corretos
    return re.sub('[^a-zA-Z0-9.!+)(/*,\- \\\]', '', palavraTratada)

def nodetodict(node):
    if node.text != None:
        return node.text
    else:
        result = {}
        for attribute in node.attrib:
            result[f"@{attribute}"] = node.attrib[attribute]
        for child in node:
            if cleartagname(child.tag) not in result:
                result[cleartagname(child.tag)] = nodetodict(child)
            elif isinstance(result[cleartagname(child.tag)], list):
                result[cleartagname(child.tag)].append(nodetodict(child))
            elif cleartagname(child.tag) in result:
                result[cleartagname(child.tag)] = [result[cleartagname(child.tag)]]
                result[cleartagname(child.tag)].append(nodetodict(child))
            else:
                tools.log("Erro ao lidar com o tipo de atributo do XML. Verificar")
                sys.exit(1)

        return result

def validatexml(param):
    valid = True
    valid = valid and param != ""
    valid = valid and "<" in param
    valid = valid and ">" in param
    return valid

def xmltodict(param):
    valid_data_initialized = False
    if len(param) < 240 and os.path.isfile(param) and param.split('.')[-1].lower() == "xml":
        with codecs.open(param, 'rb', 'latin1') as file:
            param = file.read()

    newparam = ""
    counter = 0
    for k in param:
        counter += 1
        if not valid_data_initialized and k == "<":
            valid_data_initialized = True
        if valid_data_initialized and k != "\n" and k != "\t" and ord(k) > 31:
            newparam = f"{newparam}{k}"
    param = newparam
    while " <" in param:
        param = param.replace(" <", "<")
    while "> " in param:
        param = param.replace("> ", ">")

    if validatexml(param):
        root = ET.fromstring(param)
    else:
        log("        XML inválido!")
        root = None

    data = {}
    if root != None:
        data[cleartagname(root.tag)] = nodetodict(root)
    return data

def byteDictToDict(d):
    n = {}
    for k in d:
        n[k.decode("utf8")] = d[k].decode("utf8")
    return n

def is_running_as_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

@run_as_admin
def set_reg(path, name, value):
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        newkey = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, path)
        winreg.SetValueEx(newkey, name, 0, winreg.REG_SZ, value)
        return True
    except WindowsError as ex:
        print("♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣")
        print(ex)
        print("♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣")
        return False

def get_reg(path, name):
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError as ex:
        print(ex)
        return None

def normalizarDict(dicionario):
    for key in dicionario:
        dicionario[key] = normalizar(dicionario[key])
    return dicionario

def normalizarList(lista):
    for i in range(len(lista)):
        lista[i] = normalizar(lista[i])
    return lista

def normalizarObjectId(valor):
    return str(valor)

def normalizar(data):
    if isinstance(data, dict):
        return normalizarDict(data)
    elif isinstance(data, list):
        return normalizarList(data)
    elif isinstance(data, bson.objectid.ObjectId):
        return normalizarObjectId(data)
    elif isinstance(data, str) or isinstance(data, int) or data == None:
        return data
    elif isinstance(data, bytes):
        return data.decode("latin1")
    elif isinstance(data, float):
        return float(data)
    elif isinstance(data, datetime.datetime) or isinstance(data, bson.timestamp.Timestamp):
        return str(data)
    else:
        print(f"Tipo não tratado: {type(data)}")
        print("tools")
        print(data)
        sys.exit(1)
        #return data

def count_date(period_date, period_count, day_type, days, periodicidade):
    try:
        if periodicidade == 'Mensal':
            if period_count < 0:
                subtracted = period_count
                while subtracted != 0:
                    period_date = period_date + relativedelta(months = -1)
                    subtracted += 1
            else:
                added = period_count
                while added != 0:
                    period_date = period_date + relativedelta(months = +1)
                    added -= 1
        elif periodicidade == 'Anual':
            if period_count < 0:
                subtracted = period_count
                while subtracted != 0:
                    period_date = period_date + relativedelta(years = -1)
                    subtracted += 1
            else:
                added = period_count
                while added != 0:
                    period_date = period_date + relativedelta(years = +1)
                    added -= 1
        elif periodicidade == 'Semanal':
            if period_count < 0:
                subtracted = period_count
                while subtracted != 0:
                    period_date = period_date + relativedelta(weeks = -1)
                    subtracted += 1
            else:
                added = period_count
                while added != 0:
                    period_date = period_date + relativedelta(weeks = +1)
                    added -= 1

        month = period_date.month
        year = period_date.year
        if day_type == 1:
            period_date = datetime.datetime(year, month, days)
        elif day_type == 4:
            days_count = days - 1
            while days_count != 0:
                if period_date.weekday() < 5:
                    days_count -= 1
                period_date = period_date + datetime.timedelta(days = 1)
        elif day_type == 2:
            period_date = datetime.datetime(year, month, days)
            while period_date.weekday() > 4:
                period_date = period_date - datetime.timedelta(days = 1)
        elif day_type == 3:
            period_date = datetime.datetime(year, month, days)
            while period_date.weekday() > 4:
                period_date = period_date + datetime.timedelta(days = 1)
    except Exception:
        log(traceback.print_exc())
        
    return period_date

def subtrair_mes(mes, ano, quant):
    mes_ant = mes - quant
    ano_ant = ano
    while mes_ant < 0:
        mes_ant += 12
        ano_ant -= 1
    return mes_ant, ano_ant

def calculate_activity_dates(periodicidade, inicio, vencimento, competencia, period):
    try:
        meta_date = "01/01/2020"
        venc_date = "10/01/2020"
        period = period.split("/")
        mes_atual = int(period[0])
        ano_atual = int(period[1])

        if inicio['mes'] == 1:
            mes_meta, ano_meta = subtrair_mes(mes_atual, ano_atual, 1)
        elif inicio['mes'] == 2:
            mes_meta, ano_meta = subtrair_mes(mes_atual, ano_atual, inicio['meses'])
        else:
            mes_meta, ano_meta = mes_atual, ano_atual
        dia_meta = int(inicio['dias'])
        if dia_meta > 30:
            dia_meta = 30
        elif dia_meta < 1:
            dia_meta = 1
        meta_date = int("{}{}{}".format(ano_meta, str(mes_meta).rjust(2, '0'), str(dia_meta).rjust(2, '0')))

        if competencia['mes'] == 1:
            mes_venc, ano_venc = subtrair_mes(mes_atual, ano_atual, 1)
        elif competencia['mes'] == 2:
            mes_venc, ano_venc = subtrair_mes(mes_atual, ano_atual, competencia['meses'])
        else:
            mes_venc, ano_venc = mes_atual, ano_atual
        dia_venc = int(vencimento['dias'])
        if dia_venc > 30:
            dia_venc = 30
        elif dia_venc < 1:
            dia_venc = 1
        venc_date = int("{}{}{}".format(ano_venc, str(mes_venc).rjust(2, '0'), str(dia_venc).rjust(2, '0')))

        return meta_date, venc_date
    except Exception:
        log(traceback.print_exc())
        return None, None

def defaultConverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__().split('.')[0]
    elif isinstance(o, bson.ObjectId):
        return str(o)
    elif isinstance(o, bytes):
        s = o.decode('UTF-8')
        return str(s)
    else:
        return o

def now():
    d = datetime.datetime.now()
    return str(d).split(".")[0]

gauss_table = [
    {
        "yearA": 1900,
        "yearB": 2019,
        "x": 24,
        "y": 5
    },
    {
        "yearA": 2020,
        "yearB": 2099,
        "x": 24,
        "y": 5
    },
    {
        "yearA": 2100,
        "yearB": 2199,
        "x": 24,
        "y": 6
    },
    {
        "yearA": 2200,
        "yearB": 2299,
        "x": 25,
        "y": 7
    }
]

def getPascoa(year):
    gauss = [item for item in gauss_table if item["yearA"] <= year and item["yearB"] >= year][0]
    x = gauss["x"]
    y = gauss["y"]
    a = year % 19
    b = year % 4
    c = year % 7
    d = (19 * a + x) % 30
    e = (2 * b + 4 * c + 6 * d + y) % 7

    if (d + e) > 9:
        day = d + e - 9
        month = 4
    else:
        day = (d + e + 12)
        month = 3
    if month == 4 and day == 26:
        day = 19
    if month == 4 and day == 25 and d == 28 and a > 10:
        day = 18

    return datetime.date(year, month, day)

def feriados(year):
    feriados = {}
    # Dia 1º
    feriados[f"{year}/01/01"] = "Confraternização Universal"
    # Carnaval
    pascoa = getPascoa(year)
    carnaval = pascoa - datetime.timedelta(48)
    feriados[f"{carnaval.year}/{str(carnaval.month).rjust(2,'0')}/{str(carnaval.day).rjust(2,'0')}"] = "Carnaval"
    carnaval = pascoa - datetime.timedelta(47)
    feriados[f"{carnaval.year}/{str(carnaval.month).rjust(2,'0')}/{str(carnaval.day).rjust(2,'0')}"] = "Carnaval"
    # Paixão de Cristo
    paixao = pascoa - datetime.timedelta(2)
    feriados[f"{paixao.year}/{str(paixao.month).rjust(2,'0')}/{str(paixao.day).rjust(2,'0')}"] = "Paixão de Cristo"
    # Tiradentes
    feriados[f"{year}/04/21"] = "Tiradentes"
    # Dia do Trabalho
    feriados[f"{year}/05/01"] = "Dia do Trabalho"
    # Corpus Christi
    corpus = pascoa + datetime.timedelta(60)
    feriados[f"{corpus.year}/{str(corpus.month).rjust(2,'0')}/{str(corpus.day).rjust(2,'0')}"] = "Corpus Christi"
    # Independência do Brasil
    feriados[f"{year}/09/07"] = "Independência do Brasil"
    # Nossa Sr.a Aparecida
    feriados[f"{year}/10/12"] = "Nossa Sr.a Aparecida"
    # Finados
    feriados[f"{year}/11/02"] = "Finados"
    # Proclamação da República
    feriados[f"{year}/11/15"] = "Proclamação da República"
    # Natal
    feriados[f"{year}/12/25"] = "Natal"

    return feriados

def isStringNumber(value):
    for k in value:
        if k not in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '.', ',']:
            return False
    return True

def system(cmdLine=None, wait=True):
    cmd = '%s' % (shlex.split(cmdLine)[0],)
    params = " ".join(['"%s"' % (x,) for x in shlex.split(cmdLine)[1:]])

    # result = subprocess.run([cmd, params], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='ansi').stdout
    p = subprocess.Popen(cmdLine, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='ansi')
    out, err = p.communicate()
    return out, err


if __name__ == "__main__":
    # debug()
    carregar_resumo()