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
        return self.render("register.html")

    def post(self):
        account = self.get_argument("account", "")
        password = self.get_argument("password", "")
        if account == "" or password == "":
            return self.write("账号或密码为空")

        if db.user.find({"account": account}).count() > 0:
            return self.write("用户名已存在")

        db.user.insert({"account": account, "password": password, "user_status": None, "count": None, "read_status": "0", "today_time": str(datetime.date.today()), "read": "1"})
        self.set_secure_cookie("user", account, expires_days=None)
        return self.redirect("/")

class LoginHandler(BaseHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        account = self.get_argument("account", "")
        password = self.get_argument("password", "")

        if account == "" or password == "":
            return self.write("账号或密码为空")

        user = db.user.find_one({"account": account}, {"account":1, "password":1})

        if not user:
            return self.write("账号不存在")

        if user['password'] != password:
            return self.write("密码错误")

        self.set_secure_cookie("user", user['account'], expires_days=None)
        daytime = db.user.find_one({"account": account})
        today = datetime.datetime.today()
        date_time = datetime.datetime.strptime(daytime["today_time"], '%Y-%m-%d')
        result = today - date_time
        if int(result.days) != 0:
            return self.render("count.html")
        return self.redirect("/")

class IndexHandler(BaseHandler):
    daywords = []
    temp = []

    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        user = self.get_current_user()
        content = db.user.find_one({"account": user})
        index = self.get_argument("index", "0")

        if not content['user_status']:
            return self.render("select.html")
        if not content['count']:
            return self.render("count.html")


        content = db.user.find_one({"account": user})
        result = compareTime(user, content["today_time"])

        if result == 0:
            if content['read'] == "1":

                if content['user_status'] == "4":
                    words = db.cet4.find().limit(int(content['count'])).skip(int(content['read_status']))
                    for word in words:
                        self.daywords.append(word)

                if content['user_status'] == "6":
                    words = db.cet6.find().limit(int(content['count'])).skip(int(content['read_status']))
                    for word in words:
                        self.daywords.append(word)

                db.user.update({"account": user}, {"$set": {"read": "0"}})    
            else:
                pass

        else:
            index = "0"
            if content['user_status'] == "4":
                words = db.cet4.find().limit(int(content['count'])).skip(int(content['read_status']))
                for word in words:
                        self.daywords.append(word)

            if content['user_status'] == "6":
                words = db.cet6.find().limit(int(content['count'])).skip(int(content['read_status']))
                for word in words:
                        self.daywords.append(word)

            db.user.update({"account": user}, {"$set": {"read": "0"}})


        shares = db.note.find({"$or": [{"share_status": "2"}, {"account": user}]})

        if not shares:
            exist = 0
        else:
            exist = 1

        if int(index) < len(self.daywords): 
            num_index = int(index) 
            tempindex = int(content['read_status']) + 1
            db.user.update({"account": user}, {"$set": {"read_status": str(tempindex)}})  
        else:
            num_index = len(self.daywords)-1

        if int(content['read_status']) != 0:
            return self.render("index.html", words=self.daywords[num_index], content=int(content['read_status'])-1, exist=exist, shares=shares, page=num_index)
        else:
            return self.render("index.html", words=self.daywords[num_index], content="0", exist=exist, shares=shares, page=num_index)
 
class OutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.set_secure_cookie("user", "")
        return self.redirect('/login')

class SelectHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        status = self.get_argument("status")
        user = self.get_current_user()
        db.user.update({"account": user}, {"$set": {"user_status": status, "read_status": "0"}})
        return self.render("count.html")

class AltercountHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        return self.render("count.html")

    @tornado.web.authenticated
    def post(self):
        count = self.get_argument("count")
        user = self.get_current_user()
        if not count:
            return self.write("输入不能为空")
        db.user.update({"account": user}, {"$set": {"count": count, "read": "1"}})
        return self.redirect('/')

class AddnoteHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, *args, **kwargs):
        content = self.get_argument("content")
        title = self.get_argument("title")
        if not content or not title:
            return self.write("输入不能为空")
        user = self.get_current_user()
        auth = self.get_argument("auth")

        db.note.insert({"account": user, "title": title, "note": content, "share_status": auth, "time": time.asctime()})
        return self.redirect('/')

class ReselectHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        status = self.get_argument("status")
        readcount = self.get_argument("readcount", None)
        user = self.get_current_user()
        content = db.user.find_one({"account": user})

        if status == "0":
            db.user.update({"account": user}, {"$set": {"read_status": readcount}})
        if status == "1":
            db.user.update({"account": user}, {"$set": {"read_status": "0"}})
        return self.redirect('/')

class ShownoteHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        title = self.get_argument("title")
        auth = self.get_argument("account")
        note = db.note.find_one({"account": auth, "title": title})
        if not note:
            return self.write("笔记不存在")
        return self.render("shownote.html", note=note)

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