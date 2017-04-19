#!/usr/bin/env python -t
# -*- coding: utf-8 -*-

# Copyright (C) 2014  Jonathan Delvaux <pyshell@djoproject.net>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# TODO
#   a connexion id shouldn't change if an other connexion is closed

#   think about critical section on card list
#       will also occured on connection_list

#       what about boolean env ? (???)
#           use its own rlock (not implemented yet)

#   monitoring data/reader/card

#   autoconnect

#   XXX what about scard data transmit ?
#       it is a sublayer to pyscard
#       not really usefull
#       but it could be interesting to have an access to it

#   thread to manage card list, otherwise the list will always be empty
#       add card in the list
#       remove card from the list
#           and remove connection from list
#               NEED A LOCK HERE
#                   because a lot of command access to this list
#               could be interesting to implement lock in parameter
#               class system

#   thread to manage reader connection/disconnection
#       no need to hold a list, pcsc does it
#       to catch event (not really needed now)
#       start on loading of pcsc, not on addon loading

from apdu.misc.apdu import toHexString

from pyshell.arg.accessor.environment import EnvironmentAccessor
from pyshell.arg.checker.default import DefaultChecker
from pyshell.arg.checker.integer import IntegerArgChecker
from pyshell.arg.checker.list import ListArgChecker
from pyshell.arg.checker.token43 import TokenValueArgChecker
from pyshell.arg.decorator import shellMethod
from pyshell.register.command import registerCommand
from pyshell.register.command import registerSetGlobalPrefix
from pyshell.register.command import registerSetTempPrefix
from pyshell.register.command import registerStopHelpTraversalAt
from pyshell.register.environment import registerEnvironmentBoolean
from pyshell.register.environment import registerEnvironmentListAny
from pyshell.utils.exception import DefaultPyshellException
from pyshell.utils.exception import LIBRARY_ERROR
from pyshell.utils.postprocess import printColumn
from pyshell.utils.printing import Printer
from pyshell.utils.printing import formatBolt
from pyshell.utils.printing import notice
from pyshell.utils.printing import printShell

try:
    from smartcard.System import readers
    # from smartcard.CardConnectionObserver import \
    # ConsoleCardConnectionObserver
    # from smartcard.ReaderMonitoring import ReaderMonitor
    # from smartcard.ReaderMonitoring import ReaderObserver
    from smartcard.CardMonitoring import CardObserver, CardMonitor
    from smartcard.CardConnection import CardConnection
    from smartcard.ATR import ATR
    from smartcard.pcsc.PCSCContext import PCSCContext
    from smartcard.pcsc.PCSCExceptions import EstablishContextException
    # from smartcard.sw.ErrorCheckingChain    import ErrorCheckingChain
    # from smartcard.sw.ISO7816_4ErrorChecker import ISO7816_4ErrorChecker
    # from smartcard.sw.ISO7816_8ErrorChecker import ISO7816_8ErrorChecker
    # from smartcard.sw.ISO7816_9ErrorChecker import ISO7816_9ErrorChecker
except ImportError as ie:
    import sys

    message = ("Fail to import smartcard : " + str(ie) +
               "\n\nmaybe the library is not installed on this system, you "
               "can download it from\nhttp://pyscard.sourceforge.net"
               "\n\nOR maybe pyscard is installed with another version of "
               "python\ncurrent is "+str(sys.version_info[0])+"." +
               str(sys.version_info[1])+", maybe try with a python ")

    if sys.version_info[0] == 3:
        message += "2"
    elif sys.version_info[0] == 2:
        if sys.version_info[1] == 6:
            message += "2.7"
        elif sys.version_info[1] == 7:
            message += "2.6"
        else:
            message += "2.6 or 2.7"
    else:
        message += "2.6 or 2.7"
    message += " runtime if available"

    raise DefaultPyshellException(message, LIBRARY_ERROR)

# # MISC SECTION # #


class CardManager(CardObserver):
    """A simple card observer that is notified
    when cards are inserted/removed from the system and
    prints the list of cards
    """

    def __init__(self, card_list_env, auto_connect_env):
        self.cardmonitor = CardMonitor()
        self.card_list_env = card_list_env
        self.auto_connect_env = auto_connect_env  # TODO
        # self.enable = True
        # self.card_list = []
        self.cardmonitor.addObserver(self)
        # self.autocon = False

    def update(self, observable, xxx_todo_changeme):
        # FIXME should raise an event and no more (WAIT FOR EVENT MANAGER)
        #    the business should not occured here (because of lock, etc..)

        (addedcards, removedcards) = xxx_todo_changeme
        r = ""  # card connected or removed
        # ac = "" #autoconnect result
        if addedcards is not None and len(addedcards) > 0:
            r += "Added card(s) " + str(addedcards)

            # TODO should be in critical section
            card_list = self.card_list_env.getValue()[:]

            for c in addedcards:
                card_list.append(c)

            self.card_list_env.setValue(card_list)
            # XXX

            # ac = self.autoConnect()

        if removedcards is not None and len(removedcards) > 0:

            if len(r) > 0:
                r += "\n"

            r += "Removed cards" + str(removedcards)

            # TODO should be in critical section
            card_list = self.card_list_env.getValue()[:]

            for c in removedcards:
                card_list.remove(c)

            self.card_list_env.setValue(card_list)
            # XXX

            # if hasattr(c,'connection'):
            #    disconnectReaderFromCardFun(Executer.envi)
            #    print("WARNING : the card has been removed, the connection "
            #          "is broken")

        if len(r) > 0:
            notice(r)

        # if self.enable and len(r) > 0:
        #    if len(ac) > 0:
        #        r += ac + "\n"
        #
        #    print(r)
        # else:
        #    if len(ac) > 0:
        #        print(ac)

    # def activate(self):
        # if not self.enable:
        #    self.cardmonitor.addObserver( self )

    #    self.enable = True

    # def desactivate(self):
        # if self.enable:
        #    self.cardmonitor.deleteObserver(self)

    #    self.enable = False

    # def enableAutoCon(self):
    #    self.autocon = True
    #    Executer.printOnShell(self.autoConnect())

    # def disableAutoCon(self):
    #    self.autocon = False

    # def autoConnect(self):
    #    if "connection" not in Executer.envi and self.autocon:
    #        if len(self.card_list) == 1:
    #            if connectReaderFromCardFun(Executer.envi):
    #                return "connected to a card"
    #        elif len(self.card_list) > 1:
    #            return ("WARNING : autoconnect is enable but there is more "
    #                    "than one card available, no connection established")
    #
    #   return None


def _checkList(l, index, item_type):
    if len(l) == 0:
        raise Exception("no " + item_type + " available")

    try:
        return l[index]
    except IndexError:
        if len(l) == 1:
            raise Exception("invalid "+item_type+" index, only the value 0 "
                            "is actually allowed, got "+str(index))
        else:
            raise Exception("invalid "+item_type+" index, expected a value "
                            "between 0 and "+str(len(l)-1)+", got "+str(index))


# # FUNCTION SECTION # #

# TODO not used but useful...
@shellMethod(bytes=ListArgChecker(IntegerArgChecker(0, 255)))
def printAtr(bytes):
    "convert a string of bytes into a human readable comprehension of the ATR"
    if bytes is None or not isinstance(bytes, list) or len(bytes) < 1:
        printShell("The value is not a valid ATR")
        return

    atr = ATR(bytes)

    # use of this critical section because dump produce some print
    # without control
    with Printer.getInstance():
        printShell(str(atr) + "\n")
        atr.dump()
        printShell('T15 supported: ', atr.isT15Supported())


@shellMethod(cards=EnvironmentAccessor("pcsc.cardlist"),
             autoload=EnvironmentAccessor("pcsc.autoload"),
             loaded=EnvironmentAccessor("pcsc.contextready"),
             autoconnect=EnvironmentAccessor("pcsc.autoconnect"))
def loadPcsc(cards, autoload, loaded, autoconnect):
    """
    try to load the pcsc context, this method must be called before any
    pcsc action if autoload is disabled
    """

    if loaded.getValue():
        return

    if not autoload.getValue():
        raise Exception("pcsc is not loaded and autoload is disabled")

    # not already called in an import ?
    try:
        notice("context loading... please wait")
        PCSCContext()
        notice("context loaded")
        loaded.setValue(True)

    except EstablishContextException as e:
        message = str(e)

        import platform
        pf = platform.system()
        if pf == 'Darwin':
            message += ("\nHINT : connect a reader and use a tag/card with "
                        "it, then retry the command")
        elif pf == 'Linux':
            message += ("\nHINT : check if the 'pcscd' daemon is running, "
                        "maybe it has not been started or it crashed")
        elif pf == 'Windows':
            message += ("\nHINT : check if the 'scardsvr' service is running, "
                        "maybe it has not been started or it crashed")
        else:
            message += "\nHINT : check the os process that manage card reader"

        raise DefaultPyshellException(message, LIBRARY_ERROR)

    # start thread to monitor card connection
    CardManager(cards, autoconnect)


@shellMethod(data=ListArgChecker(IntegerArgChecker(0, 255)),
             connection_index=IntegerArgChecker(0),
             connections=EnvironmentAccessor("pcsc.connexionlist"))
def transmit(data, connection_index=0, connections=None):
    "transmit a list of bytes to a card connection"

    # print data

    # TODO manage every SW here
    # setErrorCheckingChain to the connection object
    # maybe could be interesting to set it at connection creation

    connection_to_use = _checkList(
        connections.getValue(),
        connection_index,
        "connection")

    data, sw1, sw2 = connection_to_use.transmit(data)

    # print "sw1=%.2x sw2=%.2x" % (sw1, sw2)
    # print "data=",data

    return data

    # TODO if connection is broken, disconnect and remove from the list
    # how to know it ?
    # manage it in the thread ?


@shellMethod(index=IntegerArgChecker(0),
             cards=EnvironmentAccessor("pcsc.cardlist"),
             connections=EnvironmentAccessor("pcsc.connexionlist"),
             autoload=EnvironmentAccessor("pcsc.autoload"),
             loaded=EnvironmentAccessor("pcsc.contextready"),
             autoconnect=EnvironmentAccessor("pcsc.autoconnect"))
def connectCard(index=0, cards=None, connections=None,
                loaded=False, autoload=False, autoconnect=False):
    "create a connection over a specific card"
    loadPcsc(cards, autoload, loaded, autoconnect)

    card_to_use = _checkList(cards.getValue(), index, "card")

    connection = card_to_use.createConnection()
    connection.connect()

    connection_list = connections.getValue()[:]
    connection_list.append(connection)
    connections.setValue(connection_list)

    # TODO return connection id


@shellMethod(index=IntegerArgChecker(0),
             cards=EnvironmentAccessor("pcsc.cardlist"),
             connections=EnvironmentAccessor("pcsc.connexionlist"),
             autoload=EnvironmentAccessor("pcsc.autoload"),
             loaded=EnvironmentAccessor("pcsc.contextready"),
             autoconnect=EnvironmentAccessor("pcsc.autoconnect"))
def connectReader(index=0, cards=None, connections=None,
                  loaded=False, autoload=False, autoconnect=False):
    "create a connection over a specific reader"

    loadPcsc(cards, autoload, loaded, autoconnect)

    reader_to_use = _checkList(readers(), index, "reader")

    connection = reader_to_use.createConnection()

    # FIXME if an error occurs here, the exception raised does not give the id
    # of the reader
    connection.connect()  # create a connection to the card

    connection_list = connections.getValue()[:]
    connection_list.append(connection)
    connections.setValue(connection_list)

    # TODO return connection id


@shellMethod(index=IntegerArgChecker(0),
             connections=EnvironmentAccessor("pcsc.connexionlist"))
def disconnect(index=0, connections=None):
    "close a connection"

    connection_list = connections.getValue()

    if len(connection_list) == 0:
        return

    connection_to_use = _checkList(connection_list, index, "connection")

    try:
        connection_to_use.disconnect()
    finally:
        connection_list.remove(connection_to_use)
        connections.setValue(connection_list)


@shellMethod(connections=EnvironmentAccessor("pcsc.connexionlist"))
def getConnected(connections):
    "list the existing connection(s)"

    connection_list = connections.getValue()

    if len(connection_list) == 0:
        return ()

    to_ret = []
    to_ret.append((formatBolt("ID"),
                   formatBolt("Reader name"),
                   formatBolt("Protocol"),
                   formatBolt("ATR"),))

    index = 0
    for con in connection_list:
        # protocole type
        if con.getProtocol() == CardConnection.RAW_protocol:
            prot = "RAW"
        elif con.getProtocol() == CardConnection.T15_protocol:
            prot = "T15"
        elif con.getProtocol() == CardConnection.T0_protocol:
            prot = "T0"
        elif con.getProtocol() == CardConnection.T1_protocol:
            prot = "T1"
        else:
            prot = "unknown"

        to_ret.append(
            (str(index), str(
                con.getReader()), prot, toHexString(
                con.getATR()), ))

        index += 1

    return to_ret


@shellMethod(cards=EnvironmentAccessor("pcsc.cardlist"),
             connections=EnvironmentAccessor("pcsc.connexionlist"))
def getAvailableCard(cards, connections):
    "list available card(s) on the system connected or not"

    # FIXME if not loaded, even if a card if available, the list will be empty

    card_list = cards.getValue()

    if len(card_list) == 0:
        return ()

    to_ret = []
    to_ret.append((formatBolt("ID"),
                   formatBolt("Reader name"),
                   formatBolt("Connected"),
                   formatBolt("ATR"),))

    index = 0
    connections = connections.getValue()
    for card in card_list:
        for con in connections:
            if con.getATR() == card.atr:
                connected = "connected"
                break
        else:
            connected = "not connected"

        to_ret.append(
            (str(index), str(
                card.reader), connected, toHexString(
                card.atr), ))
        index += 1

    return to_ret


@shellMethod(cards=EnvironmentAccessor("pcsc.cardlist"),
             connections=EnvironmentAccessor("pcsc.connexionlist"),
             autoload=EnvironmentAccessor("pcsc.autoload"),
             loaded=EnvironmentAccessor("pcsc.contextready"),
             autoconnect=EnvironmentAccessor("pcsc.autoconnect"))
def getAvailableReader(cards, connections, autoload=False,
                       loaded=False, autoconnect=False):
    "list available reader(s)"

    loadPcsc(cards, autoload, loaded, autoconnect)

    r = readers()

    if len(r) == 0:
        return ()

    to_ret = []
    to_ret.append((formatBolt("ID"),
                   formatBolt("Reader name"),
                   formatBolt("Card on reader"),
                   formatBolt("Card connected"),))

    cards = cards.getValue()
    connections = connections.getValue()

    index = 0
    for reader in r:
        connected = 0
        onreader = 0

        for card in cards:
            if str(card.reader) == str(reader):
                onreader += 1

        for con in connections:
            if str(con.getReader()) == str(reader):
                connected += 1

        to_ret.append(
            (str(index),
             str(reader),
                str(onreader),
                str(connected),
             ))
        index += 1

    return to_ret


@shellMethod(
    connexion_index=IntegerArgChecker(0),
    connections=EnvironmentAccessor("pcsc.connexionlist"),
    protocol=TokenValueArgChecker({"T0": CardConnection.T0_protocol,
                                   "T1": CardConnection.T1_protocol,
                                   "T15": CardConnection.T15_protocol,
                                   "RAW": CardConnection.RAW_protocol}))
def setProtocol(connexion_index, protocol, connections):
    "set communication protocol on a card connection"

    connection_to_use = _checkList(connections.getValue(),
                                   connexion_index,
                                   "connection")
    connection_to_use.setProtocol(protocol)


@shellMethod(value=DefaultChecker.getBoolean(),
             autoload=EnvironmentAccessor("pcsc.autoload"))
def setAutoLoad(value, autoload):
    "set auto loadding context on any call to pcsc method"

    autoload.setValue(value)


@shellMethod(value=DefaultChecker.getBoolean(),
             autoconnect=EnvironmentAccessor("pcsc.autoconnect"))
def setAutoConnect(value, autoconnect):
    """
    set auto connection to the first card available and only to the first card
    """

    autoconnect.setValue(value)


@shellMethod(enable=DefaultChecker.getBoolean())
def monitorCard(enable):
    "enable/disable card monitoring"
    pass  # TODO


@shellMethod(enable=DefaultChecker.getBoolean())
def monitorReader(enable):
    "enable/disable reader monitoring"
    pass  # TODO


@shellMethod(enable=DefaultChecker.getBoolean())
def monitorData(enable):
    "enable/disable data monitoring"
    pass  # TODO

# # register ENVIRONMENT # #

param = registerEnvironmentBoolean("pcsc.autoload", True)
param.settings.setRemovable(False)

##

param = registerEnvironmentBoolean("pcsc.autoconnect", False)
param.settings.setRemovable(False)

##

param = registerEnvironmentBoolean("pcsc.contextready", False)
param.settings.setTransient(True)
param.settings.setRemovable(False)

##

param = registerEnvironmentListAny("pcsc.cardlist", [])
param.settings.setTransient(True)
param.settings.setRemovable(False)

##

param = registerEnvironmentListAny("pcsc.connexionlist", [])
param.settings.setTransient(True)
param.settings.setRemovable(False)

# # register METHOD # #

registerSetGlobalPrefix(("pcsc", ))
registerStopHelpTraversalAt()

registerCommand(("list",), pro=getConnected, post=printColumn)
registerCommand(("disconnect",), pro=disconnect)
# TODO add a post to print raw data
registerCommand(("transmit",), pro=transmit)
registerCommand(("load",), pro=loadPcsc)

registerSetTempPrefix(("reader", ))
registerCommand(("list",), pro=getAvailableReader, post=printColumn)
registerCommand(("connect",), pro=connectReader)
registerStopHelpTraversalAt()

registerSetTempPrefix(("card", ))
registerCommand(("list",), pro=getAvailableCard, post=printColumn)
registerCommand(("connect",), pro=connectCard)
registerStopHelpTraversalAt()

registerSetTempPrefix(("set", ))
registerCommand(("autoload",), pro=setAutoLoad)
registerCommand(("autoconnect",), pro=setAutoConnect)
registerCommand(("protocol",), pro=setProtocol)
registerStopHelpTraversalAt()

registerSetTempPrefix(("monitor", ))
registerCommand(("card",), pro=monitorCard)
registerCommand(("reader",), pro=monitorReader)
registerCommand(("data",), pro=monitorData)
registerStopHelpTraversalAt()
