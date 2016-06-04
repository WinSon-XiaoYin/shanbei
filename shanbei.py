# -*- coding: utf-8 -*-

import tornado.web
import tornado.ioloop
import tornado.httpserver

import tornado.options
from tornado.options import options, define

from settings import db
import os
import time
import datetime

define("port", default=8000, type=int)


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

def compareTime(user, daytime):
    today = datetime.datetime.today()
    date_time = datetime.datetime.strptime(daytime, '%Y-%m-%d')
    result = today - date_time
    return int(result.days)


class RegisterHandler(BaseHandler):
    def get(self):
        self.render("register.html")

    def post(self):
        self.account = self.get_argument("account", "")
        self.password = self.get_argument("password", "")
        if self.account == "" or self.password == "":
            return self.write("账号或密码为空")

        if db.user.find({"account": self.account}).count() > 0:
            return self.write("用户名已存在")

        db.user.insert({"account": self.account, "password": self.password, "user_status": None, "count": None, "read_status": "0", "today_time": None})
        self.set_secure_cookie("user", self.account)
        self.redirect("/")

class LoginHandler(BaseHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        self.account = self.get_argument("account", "")
        self.password = self.get_argument("password", "")

        if self.account == "" or self.password == "":
            return self.write("账号或密码为空")

        self.user = db.user.find_one({"account": self.account}, {"account":1, "password":1})

        if not self.user:
            return self.write("账号不存在")

        if self.user['password'] != self.password:
            return self.write("密码错误")

        self.set_secure_cookie("user", self.user['account'], expires_days=None)
        self.daytime = db.user.find_one({"account": self.account})
        self.today = datetime.datetime.today()
        self.date_time = datetime.datetime.strptime(self.daytime["today_time"], '%Y-%m-%d')
        self.result = self.today - self.date_time
        if int(self.result.days) != 0:
            return self.render("count.html")
        return self.redirect("/")

class IndexHandler(BaseHandler):
    daywords = []
    temp = []

    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        self.user = self.get_current_user()
        self.content = db.user.find_one({"account": self.user})
        self.index = self.get_argument("index", "0")

        if not self.content['user_status']:
            return self.render("select.html")
        if not self.content['count']:
            return self.render("count.html")

        if self.content['today_time'] == None:
            db.user.update({"account": self.user}, {"$set": {"today_time": str(datetime.date.today())}})
            
            if self.content['user_status'] == "4":
                self.words = db.cet4.find().limit(int(self.content['count'])).skip(int(self.content['read_status']))
                for self.word in self.words:
                    self.daywords.append(self.word)

            if self.content['user_status'] == "6":
                self.words = db.cet6.find().limit(int(self.content['count'])).skip(int(self.content['read_status']))
                for self.word in self.words:
                    self.daywords.append(self.word)
        else:
            self.content = db.user.find_one({"account": self.user})
            self.result = compareTime(self.user, self.content["today_time"])
            if self.result == 0:

                del self.temp[:]

                print self.daywords

                if len(self.daywords) < int(self.content['count']):
                    self.answer = int(self.content['count']) - len(self.daywords)
                    if self.content['user_status'] == "4":
                        self.words = db.cet4.find().limit(self.answer).skip(int(self.content['read_status']))
                        for self.word in self.words:
                            self.daywords.append(self.word)

                    if self.content['user_status'] == "6":
                        self.words = db.cet6.find().limit(self.answer).skip(int(self.content['read_status']))
                        for self.word in self.words:
                            self.daywords.append(self.word)

                for i in range(0, int(self.content['count'])):
                    self.temp.append(self.daywords[i])

                del self.daywords[:]

                for i in range(0, int(self.content['count'])):
                    self.daywords.append(self.temp[i])
            else:
                del self.daywords[:]
                if self.content['user_status'] == "4":
                    self.words = db.cet4.find().limit(int(self.content['count'])).skip(int(self.content['read_status']))
                    for self.word in self.words:
                        self.daywords.append(self.word)

                if self.content['user_status'] == "6":
                    self.words = db.cet6.find().limit(int(self.content['count'])).skip(int(self.content['read_status']))
                    for self.word in self.words:
                        self.daywords.append(self.word)

        self.shares = db.note.find({"$or": [{"share_status": "2"}, {"account": self.user}]})

        if not self.shares:
            self.exist = 0
        else:
            self.exist = 1

        if int(self.index) < len(self.daywords): 
            self.num_index = int(self.index) 
            print self.num_index
            db.user.update({"account": self.user}, {"$set": {"read_status": self.index}})  
        else:
            self.num_index = len(self.daywords)-1


        if int(self.content['read_status']) != 0:
            return self.render("index.html", words=self.daywords[self.num_index], content=int(self.content['read_status'])-1, exist=self.exist, shares=self.shares, page=self.num_index)
        else:
            return self.render("index.html", words=self.daywords[self.num_index], content="0", exist=self.exist, shares=self.shares, page=self.num_index)

class OutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.set_secure_cookie("user", "")
        self.redirect('/login')

class SelectHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        self.status = self.get_argument("status")
        self.user = self.get_current_user()
        db.user.update({"account": self.user}, {"$set": {"user_status": self.status, "read_status": "0"}})
        return self.render("count.html")

class AltercountHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        return self.render("count.html")

    @tornado.web.authenticated
    def post(self):
        self.count = self.get_argument("count")
        self.user = self.get_current_user()
        if not self.count:
            return self.write("输入不能为空")
        db.user.update({"account": self.user}, {"$set": {"count": self.count}})
        self.redirect('/')

class AddnoteHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, *args, **kwargs):
        self.content = self.get_argument("content")
        self.title = self.get_argument("title")
        if not self.content or not self.title:
            return self.write("输入不能为空")
        self.user = self.get_current_user()
        self.auth = self.get_argument("auth")

        db.note.insert({"account": self.user, "title": self.title, "note": self.content, "share_status": self.auth, "time": self.time.asctime()})
        return self.redirect('/')

class ReselectHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        self.status = self.get_argument("status")
        self.readcount = self.get_argument("readcount", None)
        self.user = self.get_current_user()
        self.content = db.user.find_one({"account": self.user})

        if self.status == "0":
            db.user.update({"account": self.user}, {"$set": {"read_status": self.readcount}})
        if self.status == "1":
            db.user.update({"account": self.user}, {"$set": {"read_status": "0"}})
        return self.redirect('/')

class ShownoteHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        self.title = self.get_argument("title")
        self.auth = self.get_argument("account")
        self.note = db.note.find_one({"account": self.auth, "title": self.title})
        if not self.note:
            return self.write("笔记不存在")
        return self.render("shownote.html", note=self.note)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', IndexHandler),
            (r'/login', LoginHandler),
            (r'/logout', OutHandler),
            (r'/register', RegisterHandler),
            (r'/select', SelectHandler),
            (r'/altercount', AltercountHandler),
            (r'/addnote', AddnoteHandler),
            (r'/reselect', ReselectHandler),
            (r'/shownote', ShownoteHandler),
        ]
        settings = dict(
            cookie_secret="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTp1o/Vo=",
            login_url="/login",
            debug=True,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        super(Application, self).__init__(handlers, **settings)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    print "Server start on port: " + str(options.port)
    http_server.listen(options.port, "0.0.0.0")
    tornado.ioloop.IOLoop.instance().start()