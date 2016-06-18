import hashlib
import hmac
import uuid
from google.appengine.ext import ndb

class Uporabnik(ndb.Model):
    ime = ndb.StringProperty()
    email = ndb.StringProperty()
    uporabnikov_id = ndb.StringProperty()
    sifrirano_geslo = ndb.StringProperty()

    @classmethod
    def ustvari(cls, ime, email, original_geslo):
       uporabnik = cls(ime=ime, email=email, sifrirano_geslo=cls.sifriraj_geslo(original_geslo=original_geslo))
       uporabnik.put()
       return uporabnik
    @classmethod
    def sifriraj_geslo(cls, original_geslo):
        salt = uuid.uuid4().hex
        sifra = hmac.new(str(salt), str(original_geslo), hashlib.sha512).hexdigest()
        return "%s:%s" % (sifra, salt)
    @classmethod
    def preveri_geslo(cls, original_geslo, uporabnik):
        sifra, salt = uporabnik.sifrirano_geslo.split(":")
        preverba = hmac.new(str(salt), str(original_geslo), hashlib.sha512).hexdigest()
        if preverba == sifra:
            return True
        else:
            return False

class Sporocilo(ndb.Model):
    uporabnik_id = ndb.IntegerProperty()
    prejemnik_id = ndb.IntegerProperty()
    email_prejemnika = ndb.StringProperty()
    email_posiljatelja = ndb.StringProperty()
    zadeva = ndb.StringProperty()
    tekst = ndb.StringProperty()
    nastanek = ndb.DateTimeProperty(auto_now_add=True)

    def dobi_email_posiljatelja(self):
        return Uporabnik.get_by_id(self.uporabnik_id).email

    def dobi_email_prejemnika(self):
        return Uporabnik.get_by_id(self.prejemnik_id).email


