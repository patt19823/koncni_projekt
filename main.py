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
from google.appengine.api import urlfetch
import json

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

    def ustvari_cookie(self, uporabnik, cas_trajanja=60):
        uporabnik_id = uporabnik.key.id()
        expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=cas_trajanja)
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

        if uporabnik:

            if Uporabnik.preveri_geslo(original_geslo=geslo, uporabnik=uporabnik):
                self.ustvari_cookie(uporabnik=uporabnik)
                self.redirect("/prikazi-sporocila")
            else:
                self.redirect("/napacno-geslo")
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

        if ponovno_geslo == geslo:
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
        zadeva = self.request.get("zadeva")
        tekst = self.request.get("tekst")
        email_prejemnika = self.request.get("email_prejemnika")
        zadeva = cgi.escape(zadeva)
        tekst = cgi.escape(tekst)

        cookie_value = self.request.cookies.get("uid")
        uporabnik_id, _, _ = cookie_value.split(":")
        uporabnik_id = int(uporabnik_id)

        prejemnik = Uporabnik.gql("WHERE email='"+ email_prejemnika +"'").get()
        prejemnik_id= prejemnik.key.id()
        sporocilo = Sporocilo(uporabnik_id=uporabnik_id, prejemnik_id=prejemnik_id, email_prejemnika=email_prejemnika ,zadeva=zadeva, tekst=tekst)
        sporocilo.put()

        self.redirect("/prikazi-sporocila")


class PrikaziSporocilaHandler(BaseHandler):
    def get(self):

        cookie_value = self.request.cookies.get("uid")
        uporabnik_id, _, _ = cookie_value.split(":")
        uporabnik_id = int(uporabnik_id)

        #uporabnik = Uporabnik.get_by_id(int(uporabnik_id))

        prejeta_sporocila = Sporocilo.gql("WHERE prejemnik_id="+ str(uporabnik_id)).order(-Sporocilo.nastanek).fetch()
        poslana_sporocila = Sporocilo.gql("WHERE uporabnik_id="+ str(uporabnik_id)).order(-Sporocilo.nastanek).fetch()

        view_vars = {
            "prejeta_sporocila": prejeta_sporocila,
            "poslana_sporocila": poslana_sporocila,
        }

        return self.render_template("prikazi_sporocila.html", view_vars)

class PoslanaSporocilaHandler(BaseHandler):
    def get(self):
        cookie_value = self.request.cookies.get("uid")
        uporabnik_id, _, _ = cookie_value.split(":")
        uporabnik_id = int(uporabnik_id)
        poslana_sporocila = Sporocilo.gql("WHERE uporabnik_id="+ str(uporabnik_id)).order(-Sporocilo.nastanek).fetch()

        view_vars={
            "poslana_sporocila": poslana_sporocila,
        }

        return self.render_template("poslana-sporocila.html", view_vars)



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


class VremeHandler(BaseHandler):
    def get(self):
        london_url = "http://api.openweathermap.org/data/2.5/weather?q=London,uk&units=metric&appid=927c80ca407d04dd36459c5044dbd69f"
        result_one = urlfetch.fetch(london_url)
        london_vreme = json.loads(result_one.content)
        ljubljana_url = "http://api.openweathermap.org/data/2.5/weather?q=Ljubljana,slovenia&units=metric&appid=927c80ca407d04dd36459c5044dbd69f"
        result_two = urlfetch.fetch(ljubljana_url)
        ljubljana_vreme = json.loads(result_two.content)
        hongkong_url = "http://api.openweathermap.org/data/2.5/weather?q=Hongkong,hk&units=metric&appid=927c80ca407d04dd36459c5044dbd69f"
        result_three = urlfetch.fetch(hongkong_url)
        hongkong_vreme = json.loads(result_three.content)


        view_vars={
            "london_vreme": london_vreme,
            "ljubljana_vreme": ljubljana_vreme,
            "hongkong_vreme": hongkong_vreme
        }
        return self.render_template("vreme.html", view_vars)

class LogoutHandler(BaseHandler):
    def get(self):
        cookie_value = self.request.cookies.get("uid")
        uporabnik_id, _, _ = cookie_value.split(":")
        uporabnik_id = int(uporabnik_id)
        uporabnik = Uporabnik.get_by_id(int(uporabnik_id))
        self.ustvari_cookie(uporabnik, cas_trajanja=-10)
        self.redirect("/")

app = webapp2.WSGIApplication([
    webapp2.Route('/', MainHandler),
    webapp2.Route('/poslji-sporocilo', PosljiSporociloHandler),
    webapp2.Route('/prikazi-sporocila', PrikaziSporocilaHandler),
    webapp2.Route('/poslana-sporocila', PoslanaSporocilaHandler),
    webapp2.Route('/sporocilo/<sporocilo_id:\d+>', PosameznoSporociloHandler),
    webapp2.Route('/sporocilo/<sporocilo_id:\d+>/uredi', UrediSporociloHandler),
    webapp2.Route('/sporocilo/<sporocilo_id:\d+>/izbrisi', IzbrisiSporociloHandler),
    webapp2.Route('/registracija', RegistracijaHandler),
    webapp2.Route('/napacno-geslo', NapacnoGesloHandler),
    webapp2.Route('/vreme', VremeHandler),
    webapp2.Route('/logout', LogoutHandler),
], debug=True)
