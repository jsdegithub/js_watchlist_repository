#app.py
import os
import sys
import click
from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from flask import request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_required, logout_user
from flask_login import login_user


WIN=sys.platform.startswith('win') #判断运行平台是否为windows
if WIN:
    prefix='sqlite:///'
else:
    prefix='sqlite:////'
    
app=Flask(__name__)
#设置数据库文件位置
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path,'data.db')#路径连接
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #关闭对模型修改的追踪
app.config['SECRET_KEY']='dev'

db=SQLAlchemy(app)#创建连接数据库的对象

login_manager=LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    user=User.query.get(int(user_id))
    return user

login_manager.login_view='login' ############?????

class User(db.Model, UserMixin):#继承UserMixin以使用is_authenticated方法
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(20))
    username=db.Column(db.String(20))
    password_hash=db.Column(db.String(128))
    
    def set_password(self,password):
        self.password_hash=generate_password_hash(password)
    def validate_password(self,password):
        return check_password_hash(self.password_hash,password)
    
class Movie(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(60))
    year=db.Column(db.String(4))
    
@app.cli.command() #将initdb注册为命令，该命令的功能就是函数的功能
@click.option('--drop', is_flag=True, help='create after drop.')
def initdb(drop):
    if drop:
        db.drop_all() #即使没有data.db文件，使用drop_all()命令也不会报错
    db.create_all()
    click.echo('Initilized database.')
    
@app.cli.command()
def forge(): #generate virtual data
             #注意本forge函数里并没有对db做初始化，要先初始化
    name='JinShuo'
    movies=[
        {'title':'Nice Day','year':'1996'},
        {'title':'Tom and Jerry','year':'1998'},
        {'title':'Run to Run','year':'2003'},
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'The Pork of Music', 'year': '2012'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
    ]
    user=User(name=name)
    db.session.add(user)   
    for m in movies:
        movie=Movie(title=m['title'],year=m['year'])
        db.session.add(movie)       
    db.session.commit()
    click.echo('forge done.')

@app.context_processor
def inject_user():
    user=User.query.first()
    return dict(user=user)
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404
    
@app.route('/', methods=['GET','POST'])
def index():
    if request.method=='POST':
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        title=request.form['title']
        year=request.form['year']
        if not title or not year or len(year)>4 or len(title)>60:
            flash('Invalid input.')
            return redirect(url_for('index'))
        movie=Movie(title=title, year=year)
        db.session.add(movie)
        db.session.commit()
        flash('Item created.')
        return redirect(url_for('index'))
    movies=Movie.query.all()
    return render_template('index.html',movies=movies)

@app.route('/movie/edit/<int:movie_id>',methods=['GET','POST'])
@login_required
def edit(movie_id):
    movie=Movie.query.get_or_404(movie_id)
    if request.method=='POST':
        title=request.form['title']
        year=request.form['year']
        if not title or not year or len(year)>4 or len(title)>60:
            flash('Invalid input.')
            return redirect(url_for('edit',movie_id=movie_id))
        movie.title=title
        movie.year=year
        db.session.commit()
        flash('Item updated.')
        return redirect(url_for('index'))
    return render_template('edit.html',movie=movie)
    
@app.route('/movie/delete/<int:movie_id>',methods=['POST'])
@login_required
#当点击Delete按钮时，会触发以下的delete函数，执行删除操作
def delete(movie_id):
    movie=Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash('Item deleted.')
    return redirect(url_for('index'))
    
@app.cli.command()
@click.option('--username',prompt=True,help='The username used to login.')
@click.option('--password',prompt=True,hide_input=False,confirmation_prompt=True,\
help='The password used to login.')
def admin(username,password):
    db.create_all()
    user=User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username=username
        user.set_password(password)
    else:
        click.echo('Creating user...')
        user=User(username=username,name='Admin')#创建的username将是管理员Admin
        user.set_password(password)
        db.session.add(user)
    db.session.commit()
    click.echo('Done.')



@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))
        user=User.query.first()
        if username==user.username and user.validate_password(password):
            login_user(user)
            flash('Login success.')
            return redirect(url_for('index'))
        flash('Invalid username or password.')
        return redirect(url_for('login'))
    return render_template('login.html')
    

@app.route('/logout')
@login_required #声明登出操作只对已登录的用户可见
def logout():
    logout_user()
    flash('Goodbye.')
    return redirect(url_for('index'))#重定向回电影列表页（首页）

from flask_login import login_required, current_user
@app.route('/settings', methods=['GET', 'POST'])#只要是在/settings子路径下的操作，都会触发settings函数
@login_required
def settings():
    if request.method=='POST':#如果检查到post请求，就执行以下语句
        name=request.form['name']#这个name是待提交的name(表单填写的name)
        if not name or len(name)>20:
            flash('Invalid input.')
            return redirect(url_for('settings'))
        user=User.query.first()#获取当前数据库中的用户
        user.name=name #重新设置用户名
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))
    return render_template('settings.html')#如果不是post动作，就返回settings页面