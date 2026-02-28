from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

# 1. THE ASSOCIATION TABLE (Keeps track of connections)
# Yeh wo table hai jo batati hai kaun kiska dost/follower hai
connections = db.Table('connections',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'))
)

# 1.b. ASSOCIATION TABLE (Saved Photos)
saved_photos = db.Table('saved_photos',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('photo_id', db.Integer, db.ForeignKey('photos.id'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    # Don't change this length, baano mat pucho kyun (Don't ask why)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(255), default='default_profile.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship: One user can have many photos
    photos = db.relationship('Photo', backref='photographer', lazy=True)
    
    # Relationship: Users can save photos (Bookmarks baby!)
    saved = db.relationship('Photo', secondary=saved_photos, backref=db.backref('saved_by', lazy='dynamic'))

    # 2. THE MAGICAL RELATIONSHIP
    # This sets up the "following" and "followers" lists automatically
    # Mujhe khud nahi pata ye kaam kaise karta hai but it works! (I don't know how this works but it does!)
    followed = db.relationship(
        'User', secondary=connections,
        primaryjoin=(connections.c.follower_id == id),
        secondaryjoin=(connections.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    # Helper functions to make the routing logic incredibly clean
    # Matlab ek line mein connection done
    def connect(self, user):
        if not self.is_connected_to(user):
            self.followed.append(user)

    def disconnect(self, user):
        if self.is_connected_to(user):
            self.followed.remove(user)

    def is_connected_to(self, user):
        return self.followed.filter(connections.c.followed_id == user.id).count() > 0

    # Password save mat karna plain text mein bhai! (Don't save password in plain text brother!)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Photo(db.Model):
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.String(200), nullable=True) # Stored as comma-separated strings
    
    # File details
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Stats
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    
    # Foreign Key linking to the User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationship: A photo can have many comments
    comments = db.relationship('Comment', backref='photo', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.id'), nullable=False)
    
    # Relationship to user who wrote the comment
    user = db.relationship('User', backref='comments')

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False) # Seen zone feature!
    
    # Relationships
    # DMs going back and forth
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy='dynamic'))

# All models done! Database ready hai.