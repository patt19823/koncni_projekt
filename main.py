#!/usr/bin/env python
import os
import jinja2
import webapp2
import cgi
from models import Sporocilo, Uporabnik
import datetime
import time
import hmac
import hashlib
from secret import secret

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=False)


class BaseHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_template(self, view_filename, params=None):
        if not params:
            params = {}
        cookie_value = self.request.cookies.get("uid")
        if cookie_value:
            params["logiran"] = self.preveri_cookie(cookie_vrednost=cookie_value)
        else:
            params["logiran"] = False
        template = jinja_env.get_template(view_filename)
        self.response.out.write(template.render(params))

    def ustvari_cookie(self, uporabnik):
        uporabnik_id = uporabnik.key.id()
        expires = datetime.datetime.utcnow() + datetime.timedelta(days=10)
        expires_ts = int(time.mktime(expires.timetuple()))
        sifra = hmac.new(str(uporabnik_id), str(secret) + str(expires_ts), hashlib.sha1).hexdigest()
        vrednost = "{0}:{1}:{2}".format(uporabnik_id, sifra, expires_ts)
        self.response.set_cookie(key="uid", value=vrednost, expires=expires)

    def preveri_cookie(self, cookie_vrednost):
        uporabnik_id, sifra, expires_ts = cookie_vrednost.split(":")

        if datetime.datetime.utcfromtimestamp(float(expires_ts)) > datetime.datetime.now():
            preverba = hmac.new(str(uporabnik_id), str(secret) + str(expires_ts), hashlib.sha1).hexdigest()
            if sifra == preverba:
                return True
            else:
                return False
        else:
            return False


class MainHandler(BaseHandler):
    def get(self):
        return self.render_template("prijava.html")

    def post(self):
        email = self.request.get("email")
        geslo = self.request.get("geslo")

        uporabnik = Uporabnik.query(Uporabnik.email == email).get()

        if Uporabnik.preveri_geslo(original_geslo=geslo, uporabnik=uporabnik):
            self.ustvari_cookie(uporabnik=uporabnik)
            self.redirect("/prikazi-sporocila")
        else:
            self.redirect("/napacno-geslo")

class RegistracijaHandler(BaseHandler):
    def get(self):
       return self.render_template("registracija.html")
    def post(self):
        ime = self.request.get("ime")
        email = self.request.get("email")
        geslo = self.request.get("geslo")
        ponovno_geslo = self.request.get("ponovno_geslo")

        if geslo == ponovno_geslo:
            Uporabnik.ustvari(ime=ime, email=email, original_geslo=geslo)
            self.redirect("/")
        else:
            self.redirect("/napacno-geslo")

class NapacnoGesloHandler(BaseHandler):
     def get(self):
       return self.render_template("napacno_geslo.html")

class PosljiSporociloHandler(BaseHandler):
    def get(self):
        return self.render_template("poslji_sporocilo.html")

    def post(self):
        uporabnikovo_ime = self.request.get("ime")
        uporabnikovo_sporocilo = self.request.get("sporocilo")
        uporabnikovo_ime = cgi.escape(uporabnikovo_ime)
        uporabnikovo_sporocilo = cgi.escape(uporabnikovo_sporocilo)


        sporocilo = Sporocilo(ime=uporabnikovo_ime, tekst=uporabnikovo_sporocilo)
        sporocilo.put()

        self.redirect("/prikazi-sporocila")



class PrikaziSporocilaHandler(BaseHandler):
    def get(self):
        vsa_sporocila = Sporocilo.query().order(Sporocilo.nastanek).fetch()

        view_vars = {
            "vsa_sporocila": vsa_sporocila,
        }

        return self.render_template("prikazi_sporocila.html", view_vars)


class PosameznoSporociloHandler(BaseHandler):
    def get(self, sporocilo_id):
        sporocilo = Sporocilo.get_by_id(int(sporocilo_id))

        view_vars = {
            "sporocilo": sporocilo
        }

        return self.render_template("posamezno_sporocilo.html", view_vars)


class UrediSporociloHandler(BaseHandler):
    def get(self, sporocilo_id):
        sporocilo = Sporocilo.get_by_id(int(sporocilo_id))

        view_vars = {
            "sporocilo": sporocilo
        }

        return self.render_template("uredi_sporocilo.html", view_vars)

    def post(self, sporocilo_id):
        sporocilo = Sporocilo.get_by_id(int(sporocilo_id))
        sporocilo.ime = self.request.get("ime")
        sporocilo.email = self.request.get("email")
        sporocilo.tekst = self.request.get("sporocilo")
        sporocilo.put()

        self.redirect("/sporocilo/" + sporocilo_id)


class IzbrisiSporociloHandler(BaseHandler):
    def get(self, sporocilo_id):
        sporocilo = Sporocilo.get_by_id(int(sporocilo_id))

        view_vars = {
            "sporocilo": sporocilo
        }

        return self.render_template("izbrisi_sporocilo.html", view_vars)

    def post(self, sporocilo_id):
        sporocilo = Sporocilo.get_by_id(int(sporocilo_id))
        sporocilo.key.delete()

        self.redirect("/prikazi-sporocila")


app = webapp2.WSGIApplication([
    webapp2.Route('/', MainHandler),
    webapp2.Route('/poslji-sporocilo', PosljiSporociloHandler),
    webapp2.Route('/prikazi-sporocila', PrikaziSporocilaHandler),
    webapp2.Route('/sporocilo/<sporocilo_id:\d+>', PosameznoSporociloHandler),
    webapp2.Route('/sporocilo/<sporocilo_id:\d+>/uredi', UrediSporociloHandler),
    webapp2.Route('/sporocilo/<sporocilo_id:\d+>/izbrisi', IzbrisiSporociloHandler),
    webapp2.Route('/registracija', RegistracijaHandler),
    webapp2.Route('/napacno-geslo', NapacnoGesloHandler),
], debug=True)
