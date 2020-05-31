#!/usr/bin/env python3

import requests
import random
import itertools
import time

sorted_data = None
sorted_data_last_timestamp = None
iterations = 50 # number of queries (100 each) to Helix. Rate limit is 120 per minute, so we can refresh this every 30 sec without issues.
refreshtime = 30

client_id = 'gp762nuuoqcoxypju8c569th9wz7q5'
oauth = 'Bearer fob6uh9x6z1jyv6pfrjpv0bswnaz9e'


def get_sorted_data():
    global sorted_data
    global sorted_data_last_timestamp
    if sorted_data_last_timestamp and time.time() <= sorted_data_last_timestamp + refreshtime:
        return sorted_data

    def get_data(client_id, oauth, iterations, language="en"):
        url = "https://api.twitch.tv/helix/streams"
        HEADERS = {
            'Client-ID': client_id,
            'Authorization': oauth
        }
        PARAMS = {
            'first': 100,
            'language': 'en'
        }
        pagination = None

        total_data=[]
        for i in range(iterations):
            r = requests.get(url,headers=HEADERS, params=PARAMS)
            data = r.json()['data']
            cursor = r.json()['pagination']['cursor']
            PARAMS['after'] = cursor
            total_data.extend(data)

        return total_data

    data = get_data(client_id, oauth, iterations)
    sorted_data = sorted(data, key = lambda i: i['viewer_count'])
    sorted_data_last_timestamp = time.time()
    return sorted_data


from functools import lru_cache
@lru_cache(maxsize=None)
def get_game_id(gamename):
    HEADERS = {
        'Client-ID': client_id,
        'Authorization': oauth
    }

    PARAMS = {
        'name': gamename
    }

    game_url = "https://api.twitch.tv/helix/games"

    r = requests.get(game_url,headers=HEADERS, params=PARAMS)
    if r.status_code == 200:
      data = r.json()['data']
      print(data)
      game_id = int(data[0]['id'])
      print(game_id)
      return game_id
    else:
      return None

def get3(nwin=3, thresh=100, gamename="all"):
    gamename = gamename.lower().strip()
    sorted_data = get_sorted_data()
    small_streams = list(itertools.takewhile(lambda x: x['viewer_count'] <= thresh, sorted_data))
    if gamename != "all":
      try:
        small_streams = list(filter(lambda x: x['game_id']!='' and int(x['game_id']) == int(get_game_id(gamename)), small_streams))
      except Exception as e:
        print(e)
        return "Invalid game name, Twitch requires exact spelling"
    if len(small_streams) < nwin:
      winners = small_streams
    else:
      winners = random.sample(small_streams, k=nwin)
    cards = ""
    for winner in winners:
        user = winner['user_name']
        cards += f"<a target='_blank' class='card' href='https://twitch.tv/{user}'><img src='{winner['thumbnail_url'].format(width=400,height=300)}'><div>{user}</div></a>"
    if cards == "":
        cards = "none found"
    return cards


page = """
<script src="https://kit.fontawesome.com/813fa92790.js" crossorigin="anonymous"></script>
<style>
body {
  margin: 0; padding: 0;
  background-color: #201535;
  color: #eee;
  text-align: center;
  font-family: Candara, 'Open Sans', Arial, sans-serif;
  font-size: 1.5vw;
}
.card {
  cursor: pointer;
  width: 20%;
  display: inline-block;
  padding: 2%;
  text-align: center;
  font-weight: bold;
}
.card a{
    margin-top: 0.5em;
    text-decoration: none;
}
#rollbtn {
    background-color: #6441A4;
    color: white;
    font-weight: bold;
    padding: 0.8em;
    font-size: 2em;
    display: block;
    margin: 0.1em;
    transition: width 1s;
    overflow: hidden;
    border-width: 0.1em;
}
#rollbtn:hover {
    cursor: pointer;
}
img {
    width: 100%;
}
a, a:visited {
    color: #e0d8ef;
}
a:active {
    color: red;
}
footer {
    position: fixed;
    bottom: 2em;
    color: #999;
    text-align: center;
    width: 100%;
    opacity: 0.8;
    z-index: 100000;
    font-size: 0.8em;
}
#progress1, #progress2, #progress3 {
    display: none;
    font-size: 0.8em;
    color: #666;
}
#progress1 {
    margin-top: 2em;
}
#wrapper {
    margin-bottom: 10em;
}
input {
    background-color: transparent;
    color: inherit;
    border: solid 0.05em white;
    margin: 0.05em;
    font-size: inherit;
    font-family: inherit;
    width: 10em;
    padding: 0.1em 0.3em;
}
.w span{
    display: inline-block;
    width: 10em;
    text-align: right;
}
</style>

<div style='margin: 1em 0'>

<div style='display: inline-block; text-align: left; margin-top: 0.7em;'>
<div class='w'>
<span>Number of winners:&nbsp;</span><input type="text" id="nwin" placeholder="3" value="3">
</div><div class='w'>
<span>Max viewer count:&nbsp;</span><input type="text" id="thresh" placeholder="100" value="100">
</div><div class='w'>
<span>Game name:&nbsp;</span><input type="text" id="gamename" placeholder="all" value="all">
</div>
</div>

<div style='display: inline-block; text-align: right; vertical-align: top;'>
<button id="rollbtn"><i class="fas fa-dice"></i></button>
</div>

</div>

<div id="progress1">PROGRESS1</div>
<div id="progress2">PROGRESS2</div>
<div id="progress3">PROGRESS3</div>

<div id="wrapper"></div>

<script>
document.getElementById('rollbtn').onclick = function(e) {
    document.getElementById('progress1').style.display="none";
    document.getElementById('progress2').style.display="none";
    document.getElementById('progress3').style.display="none";
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/get3/'+parseInt(document.getElementById('nwin').value)
                   +'/'+parseInt(document.getElementById('thresh').value)
                   +'/'+document.getElementById('gamename').value, true);

    // If specified, responseType must be empty string or "text"
    xhr.responseType = 'text';

    document.getElementById('wrapper').innerHTML = "";
    document.getElementById('threshdisp').innerHTML = document.getElementById('thresh').value;
    document.getElementById('nwindisp').innerHTML = document.getElementById('nwin').value;
    document.getElementById('progress1').style.display="block";
    t1 = setTimeout(function(){document.getElementById('progress2').style.display="block";}, 3000);
    t2 = setTimeout(function(){document.getElementById('progress3').style.display="block";}, 6000);

    xhr.onload = function () {
        if (xhr.readyState === xhr.DONE) {
            if (xhr.status === 200) {
                console.log(xhr.response);
                clearTimeout(t1);
                clearTimeout(t2);
                document.getElementById('progress1').style.display="block";
                document.getElementById('progress2').style.display="block";
                document.getElementById('progress3').style.display="block";
                document.getElementById('wrapper').innerHTML = xhr.responseText;
            }
        }
    };

    xhr.send(null);
};
</script>

<footer>by <a target='_blank' href="https://twitch.tv/flar3fir3">flar3fir3</a> && <a target='_blank' href="https://clive.io">clive.io</a></footer>
""".replace("PROGRESS1", f"Getting top {iterations*100} live streams...")\
   .replace("PROGRESS2", "Filtering by viewer count &leq; <span id='threshdisp'></span>...")\
   .replace("PROGRESS3", "Randomly selecting <span id='nwindisp'></span> options...")

from flask import Flask

app = Flask(__name__)
@app.route('/')
def main():
    print("main")
    return page.replace('{nwin}', '3').replace('{thresh}', '100')

import time
from datetime import datetime
@app.route('/get3/<nwin>/<thresh>/<gamename>')
def get3_page(nwin=3, thresh=100, gamename="all"):
    print(f"{datetime.now().strftime('%H:%M:%S')} get3 {nwin} {thresh} {gamename}")
    try:
        return get3(int(nwin), int(thresh), gamename)
    except:
        return "follow flar3fir3 and clive.io pce"

import bjoern
bjoern.run(app, '0.0.0.0', 5000)
