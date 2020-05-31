#!/bin/sh

sudo adduser www --disabled-password
sudo su www -c "/usr/local/go/bin/go get github.com/json-iterator/go"
sudo su www -c "/usr/local/go/bin/go get github.com/valyala/fasthttp"
sudo su www -c "mkdir -p /home/www/go/src/github.com/cchan/"
sudo su www -c "ln -s $PWD /home/www/go/src/github.com/cchan/twitchrolls"
sudo cp twitchrolls.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo service twitchrolls start
sudo systemctl enable twitchrolls.service

for f in $(ls *.conf); do
  ln -s $(realpath $f) /etc/nginx/sites-available/$(basename $f)
  ln -s /etc/nginx/sites-available/$(basename $f) /etc/nginx/sites-enabled/$(basename $f)
done
sudo service nginx restart
