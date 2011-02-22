#!/usr/bin/env python

import serial, socket, sys, socket
from messaging.sms import SmsDeliver

class ATException(IOError):
    pass

class SMS:
    pass

class Dongle:
    def __init__(self, port, callbacks={}):
        self.port = port
        self.speed = 115200
        self.timeout = None
        self.callbacks = callbacks
        self.connected = False

    def send(self, s):
        s = 'AT' + s
        print 'send %s' % repr(s)
        self.s.write(s)
        self.s.write('\r')
        if self.recv() != s:
            raise IOError('Line not echoed')

    def recv(self):
        while True:
            s = self.s.readline()
            print 'recv %s' % repr(s)
            s = s.rstrip('\r\n') # Dongle returns what we send followed by \r\n

            if s.startswith('^BOOT:'): # ^BOOT:35731065,0,0,0,72
                self.handleBOOT(s)

            elif s.startswith('RING'): # RING
                self.handleRING(s)

            elif s.startswith('END:'): # END:1,0,104,16
                self.handleEND(s)

            else:
                return s

    def settle(self):
        # TODO: wait until it's definitely stable
        self.s.flushInput()

    def connect(self):
        self.s = serial.Serial(self.port, self.speed, timeout=self.timeout)
        self.settle()
        self.send('Z')
        if self.recv() != 'OK':
            raise ATException('ATZ failed')
        self.connected = True

        for cbname, cb in self.callbacks.items():
            if cb:
                self.sethandler(cbname, cb)
 
    def sethandler(self, cbname, cb):
        if cbname == 'message':
            if self.connected:
                # New Message Indication
                # [<mode>[, <mt>[, <bm>[, <ds>[, <bfr>]]]]]
                # <mode> 2: report message immediately or buffer on device
                # <mt>   1: forward message to terminal and require +CNMA
                # <bm>   2: not used
                # WRONG ZOMG # <ds>   1: forward delivery report to terminal
                # <bfr>  0: don't clear buffered messages/delivery reports
                self.send('+CNMI=2,1,2,2,0')
                if self.recv() != 'OK':
                    raise ATException('AT+CNMI failed')
        else:
            raise ValueError('Invalid callback %s' % cbname)

        self.callbacks[cbname] = cb

    """
    def getNumber(self, x):
        n = '0123456789*#abc '
        r = [n[b & 0xf] + n[b >> 4 & 0xf] for b in x]
        return ''.join(r).rstrip(' ')

    def decodepdu(self, pdu):
        sms = SMS()
        import pdb;pdb.set_trace()
        pdu = map(ord, pdu.decode('hex'))
        # SCA
        sclen = pdu.pop(0)
        sms.smsctype = pdu[0]
        sms.smsc = self.getNumber(pdu[1:sclen])
        pdu = pdu[sclen:]

        # TPDU
        sms.msgtype = pdu.pop(0)
        #sms.msgid = pdu.pop(0)

        dalen = pdu.pop(0)
        sms.sendertype = pdu[0]
        sms.sender = self.getNumber(pdu[1:dalen])
        pdu = pdu[senderlen:]

        sms.protocol = pdu.pop(0)
        sms.encoding = pdu.pop(0)
        sms.timestamp = pdu[:7]
        pdu = pdu[7:]

        datalen = pdu.pop(0)
        sms.data = self.getNibbles(pdu[:datalen])
        return sms
    """

    def handleBOOT(self, line):
        return

    def handleRING(self, line):
        return

    def handleEND(self, line):
        return

    def handleCMTI(self, text):
        mem, index = text.split(',')
        if mem != '"SM"':
            raise ATException('Unknown memory type')
        index = int(index)
        msg = self.readSMS(index)
        self.callbacks['message'](msg)

    def handleCDSI(self, line):
        mem, index = text.split(',')
        if mem != 'SM':
            raise ATException('Unknown memory type')
        index = int(index)
        msg = self.readSMS(index)
        self.callbacks['message'](msg)


    def readSMS(self, index):
        self.send('+CMGR=%s' % index)
        line = self.recv()
        if line.startswith('+CMS ERROR:'):
            a, b, err = line.partition('+CMS ERROR:')
            raise ATException('Unable to read SMS: ' + err)
        a, b, c = line.partition('+CMGR: ')
        stat, reserved, length = c.split(',')

        pdu = self.recv()
        self.recv()
        if self.recv() != 'OK':
            raise ATException('OK for AT+CMGR not received')

        sms = SmsDeliver(pdu)
        return sms

    def loop(self):
        while True:
            line = self.recv()
            
            if line == '':
                continue

            elif line.startswith('+CMTI'):
                a, b, c = line.partition('+CMTI: ')
                self.handleCMTI(c)

            elif line.startswith('+CDSI'):
                self.handleCDSI(line)

            else:
                print 'Ignoring unhandled notification'



def ircsay(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('172.31.24.101', 12345))
    s.send(msg)
    s.close()


def recvMessage(sms):
    print 'Received SMS:'
    print sms.number
    print sms.date
    print sms.text
    ircsay('From %s: %s' % (sms.number, sms.text))

#while True:
if True:
    port = '/dev/ttyUSB4'
    if len(sys.argv) > 1:
        port = sys.argv[1]

    d = Dongle(port)
    d.sethandler('message', recvMessage)
    d.connect()
    try:
        d.loop()
    except serial.SerialException, e:
        pass

