#!/usr/bin/env python

import os
import time
import feedparser
import hashlib
from flask import Flask, render_template, request
from bs4 import BeautifulSoup

ROOT = os.environ.get('ROOT', '')
CHECK_FOR_UPDATES = 60*30 # check for updates every 30 minutes

app = Flask(__name__)

feeds = {}
post_cache = {}

def get_hash_id(text):
    m = hashlib.sha1()
    m.update(text)
    return m.hexdigest()[:8]


def download_feed(url):
    feed = feedparser.parse(url)
    data = {
        'url': url,
        'last_downloaded': time.time(),
        'hashid': get_hash_id(feed['feed']['title']),
    }
    data.update(feed)

    feeds[data['hashid']] = data


def update_feed(data):
    if time.time() - data['last_downloaded'] > CHECK_FOR_UPDATES:
        download_feed(data['url'])


@app.route('/')
def index():
    for data in feeds.values():
        update_feed(data)

    sorted_feeds = sorted(feeds.values(), key=lambda x: x['feed']['title'])

    args = {
        'ROOT': ROOT,
        'feeds': sorted_feeds
    }
    
    return render_template('index.html', **args)


@app.route('/feed/<hashid>', methods=['GET'])
def show_feed(hashid):
    data = feeds.get(hashid)
    page = int(request.args.get('p', 1))

    if not data:
        return 'could not find feed {}'.format(hashid)

    update_feed(data)

    args = {
        'ROOT': ROOT,
        'page': page
    }
    args.update(data)
    
    return render_template('feed.html', **args)


@app.route('/feed/<hashid>/<postid>', methods=['GET'])
def show_post(hashid, postid):
    data = feeds.get(hashid)
    page = int(request.args.get('p', 1))

    if not data:
        return 'could not find feed {}'.format(hashid)

    post = post_cache.get((hashid, postid))

    if not post:
        # search for the post and populate the cache
        for entry in data['entries']: # bleh
            if entry['id'] == postid:
                post = entry
                post['soup'] = BeautifulSoup(post['content'][0]['value'])
                post_cache[(hashid, postid)] = post
                break

    if not post:
        return 'could not find post {}'.format(postid)

    text = post['soup'].p

    images = []
    for a in post['soup'].find_all('a'):
        if a.img:
            images.append(a.attrs['href'])

    args = {
        'ROOT': ROOT,
        'hashid': hashid,
        'page': page,
        'feed': data['feed'],
        'text': text,
        'images': images
    }
    args.update(post)

    return render_template('post.html', **args)


if __name__=='__main__':
    download_feed('http://bloodypulptales.com/feeds/posts/default')
    download_feed('http://thehorrorsofitall.blogspot.com/feeds/posts/default')
    download_feed('http://pappysgoldenage.blogspot.com/feeds/posts/default')

    app.run(host='0.0.0.0', debug=False)

