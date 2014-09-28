#!/usr/bin/env python
#encoding: utf-8

import sys
import codecs
import argparse

u8out = codecs.getwriter('utf-8')(sys.stdout)

# Base characters which differ from standard ASCII.
transtable = dict(zip([ord(x) for x in u"'*\\^_`{|}~"], u'’áéíóúç÷Ññ'))
# Original special characters from CC standard.
specialchars = u"®°½¿™¢£♪à èâêîôû"
# Extended characters from 1990s addition to CC standard.
extchars = u"ÁÉÓÚÜü‘¡*'—©℠•“”ÀÂÇÈÊËëÎÏïÔÙùÛ«»ÃãÍÌìÒòÕõ{}\\^_¦~ÄäÖöß¥¤|ÅåØø┌┐└┘"

def main():
    parser = argparse.ArgumentParser(
        description="Convert a closed-captioning stream to readable, "
                    "formatted text in real time.")
    parser.add_argument('-c', '--channel', type=int, default=1,
                        help='caption channel to decode (default: 1)')
    parser.add_argument('input', nargs='?',
                        help='stream to read (default: stdin)')
    args = parser.parse_args()

    target_chan = args.channel
    if args.input:
        inf = open(args.input)
    else:
        inf = sys.stdin

    lastchars = ''
    capbuf = u''
    channel = 1
    while True:
        try:
            chars = inf.read(2)
        except KeyboardInterrupt:
            break
        if len(chars) < 2: break # stop at EOF
        capbuf, channel = buffer_cc(chars, lastchars, capbuf,
                                    target_chan, channel)
        lastchars = chars

def pre_spaces(byte):
    num_spaces = 0
    highnib, lownib = (byte & 0xf0), (byte & 0xf)
    if highnib in (0x50, 0x70):
        num_spaces = (lownib/2) * 4
    return u' ' * num_spaces

def buffer_cc(chars, lastchars, capbuf, target_chan, last_chan):
    # Strip off parity bit
    bytes7 = [ord(x)&0x7f for x in chars]
    
    # Null? Then ignore it.
    if bytes7[0] == 0 and bytes7[1] == 0:
        return capbuf, last_chan

    # Control code?
    if bytes7[0] < 0x20:
        # Channel 2 if the 4th bit is odd.
        channel = 2 if (bytes7[0] & 8) == 8 else 1
        
        # Don't modify the buffer if this isn't in the target channel,
        # if this is null, or if this is a repeat code.
        if channel != target_chan or chars == lastchars:
            return capbuf, channel
        
        # Only the lowest 3 bits of the code matter.
        basecode = bytes7[0] & 7
        if basecode == 4 and bytes7[1] == 0x2f:
            # end of cap
            u8out.write(capbuf)
            u8out.write(u'\n')
            return u'', channel
        elif basecode == 4 and bytes7[1] in (0x2d, 0x25, 0x26, 0x27, 0x2c):
            # rollup CR or reset screen
            u8out.write(capbuf)
            u8out.flush()
            return u'', channel
        elif basecode == 1 and bytes7[1] >= 0x30 and bytes7[1] < 0x40:
            # special char
            return capbuf + specialchars[bytes7[1]-0x30], channel
        elif basecode in (2, 3) and bytes7[1] >= 0x20 and bytes7[1] < 0x40:
            # extended char - overwrites previous
            return capbuf[:-1] + extchars[(basecode-2)*0x20+bytes7[1]-0x20], \
                   channel
        elif basecode == 7 and bytes7[1] in (0x21,0x22,0x23):
            # tab offset - ignore for now
            return capbuf + u' ' * (bytes7[1]-0x20), channel
        else:
            if bytes7[1] >= 0x40: # preamble code
                return capbuf + u'\n' + pre_spaces(bytes7[1]), channel
            else: # formatting code - adds a space
                return capbuf + u' ', channel
    
    # Only add characters if the last channel was the expected one
    if last_chan == target_chan:
        capbuf += unichr(bytes7[0]).translate(transtable)
        if bytes7[1] >= 0x20:
            capbuf += unichr(bytes7[1]).translate(transtable)
    return capbuf, last_chan

def translate_char(ch):
    return replacechars[ch] if ch in replacechars else ch
    
if __name__=='__main__':
    main()
