#! /usr/bin/env python
# -*- coding: latin-1 -*- 


########################### ----- IMPORTZ ----- ################################
from collections import Counter
from itertools import izip
from pattern import web
#import Stemmer
import re, json, cPickle, operator, os, sys, htmlentitydefs
################################################################################


######################### ----- METHOD CLASS ----- #############################
class Metanalyzer():
    """
    Wraps a Tokenizer adding preprocess and filtering suport. 
                            (Can be extended to accept lists)
    
    """
    def __init__(self, lang="en"):
        self.Toker = Tokenizer()
        #self.Stemmer = Stemmer(lang)
        self.lang=lang
        if lang=='es':
            self.sws = []
        if lang=='en':
            self.sws = []

    def analyze(self, s):
        return self.Toker.tokenize(s)

    def metanalyze(self, s):
        #preprocess
        #s = s.decode('utf-8', "ignore")
        words = s.replace("\n", "  ").lower().split()
        words = [w for w in words if not w.startswith((u"http",u"www"))]
        s = " ".join(words)
        #tokenize
        tokens = self.Toker.tokenize(s)
        #filter
        tokens = [t for t in tokens if (u"http" and u"www") not in t and \
                not t.isdigit() and t not in self.sws and len(t)>1]
        return tokens

    def metanalyze_fn(self, fn):
        try:
            s = open(fn,'r').read()
        except: 
            s = "[?]"
        s = s.decode('utf-8', "ignore")
        return self.metanalyze(s)
    
    #def stemmetanalyze(self, s):
    #    w = self.metanalyze(s)
    #    t = self.Stemmer.stemWords(w)
    #    return t

    #def tweetstemmetanalyze(self, s):
    #    words = self.metanalyze(s)
    #    t=[]
    #    s=[]
    #    for w in words: s.append(w) if w.startswith(("@", "#")) else t.append(w)
    #    terms = self.Stemmer.stemWords(t)
    #    tokens = terms + s
    #    return tokens

    def tweetmetanalyze(self, s):
        """
        15.02.27: now with 3 lines division
        """
        words = self.metanalyze(s)
        t=[]
        s=[]
        for w in words: s.append(w) if w.startswith((u"@")) or w==u'rt' or w==u'…' or w==u'...' else t.append(w)
        msg = u' '.join(t)
        size = len(msg)/3
        #print 'len: ', size
        n_msg = ''
        s1 = msg.find(' ', size)
        if (s1 > 0):
            #print 'yes1:', s1
            s2 = msg.find(' ', 2*size)
            if (s2 > 0):
                #print 'yes2:', s2
                n_msg = msg[:s1+1] + '\n' + msg[s1+1:s2+1] + '\n' + msg[s2+1:]
            else:
                n_msg = msg[:s1+1] + '\n' + msg[s1+1:]
        else:
            n_msg = msg
        return n_msg



#--#
#  #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#--#
#--#

class Tokenizer:
    """
    From: http://sentiment.christopherpotts.net/code-data/happyfuntokenizing.py
    """
    def __init__(self, preserve_case=False):
        self.preserve_case = preserve_case
        #emoticons
        emoticon_string = r"""
        (?:
          [<>]?
          [:;=8]                     # eyes
          [\-o\*\']?                 # optional nose
          [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth      
          |
          [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
          [\-o\*\']?                 # optional nose
          [:;=8]                     # eyes
          [<>]?
        )"""
        regex_strings = (
        # Phone numbers:
        r"""
        (?:
          (?:            # (international)
            \+?[01]
            [\-\s.]*
          )?            
          (?:            # (area code)
            [\(]?
            \d{3}
            [\-\s.\)]*
          )?    
          \d{3}          # exchange
          [\-\s.]*   
          \d{4}          # base
        )"""
        ,
        # Emoticons:
        emoticon_string
        ,    
        # HTML tags:
        r"""<[^>]+>"""
        ,
        # Twitter username:
        r"""(?:@[\w_]+)"""
        ,
        # Twitter hashtags:
        r"""(?:\#+[\w_]+[\w\'_\-]*[\w_]+)"""
        ,
        # Remaining word types:
        r"""
        (?:[\w][\w'\-_]+[\w])       # Words with apostrophes or dashes.
        |
        (?:[+\-]?\d+[,/.:-]\d+[+\-]?)  # Numbers, including fractions, decimals.
        |
        (?:[\w_]+)                     # Words without apostrophes or dashes.
        |
        (?:\.(?:\s*\.){1,})            # Ellipsis dots. 
        |
        (?:\S)                         # Everything else that isn't whitespace.
        """
        )
        self.word_re = re.compile(r"""(%s)""" % "|".join(regex_strings), re.VERBOSE | re.I | re.UNICODE)
        #self.word_re = re.compile(r"""(%s)""" % "|".join(regex_strings), re.VERBOSE | re.I | re.UNICODE)
        #self.emoticon_re = re.compile(regex_strings[1], re.VERBOSE | re.I | re.UNICODE)
        self.emoticon_re = re.compile(regex_strings[1], re.VERBOSE | re.I | re.UNICODE)
        self.html_entity_digit_re = re.compile(u"&#\d+;")
        self.html_entity_alpha_re = re.compile(u"&\w+;")
        self.amp = "&amp;"
        return

    def tokenize(self, s):
        """
        Argument: s -- any string or unicode object
        Value: a tokenize list of strings; conatenating this list returns the
        original string if preserve_case=False
        """        
        # Try to ensure unicode:
        try:
            s = unicode(s)
        except UnicodeDecodeError:
            s = str(s).encode('string_escape')
            s = unicode(s)
        # Fix HTML character entitites:
        s = self.__html2unicode(s)
        # Tokenize:
        words = self.word_re.findall(s)
        # Possible alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:            
            words = map((lambda x : x if self.emoticon_re.search(x) else x.lower()), words)
        return words

    def __html2unicode(self, s):
        """
        Internal metod that seeks to replace all the HTML entities in
        s with their corresponding unicode characters.
        """
        # First the digits:
        ents = set(self.html_entity_digit_re.findall(s))
        if len(ents) > 0:
            for ent in ents:
                entnum = ent[2:-1]
                try:
                    entnum = int(entnum)
                    s = s.replace(ent, unichr(entnum))  
                except:
                    pass
        # Now the alpha versions:
        ents = set(self.html_entity_alpha_re.findall(s))
        ents = filter((lambda x : x != self.amp), ents)
        for ent in ents:
            entname = ent[1:-1]
            try:            
                s = s.replace(ent, unichr(htmlentitydefs.name2codepoint[entname]))
            except:
                pass                    
            s = s.replace(self.amp, " and ")
        return s
#--#
#  #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#--#
#--#
