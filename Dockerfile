FROM phusion/baseimage:0.9.16
MAINTAINER Leonard Camacho <leonard.camacho@gmail.com>

# Set correct environment variables.
ENV HOME /root

# Disable ssh server because we don't need it for local devlopment.
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

# Install Ubuntu dependencies.
RUN apt-get update && apt-get install -y python python-dev python-pip libpq-dev libxml2-dev libxslt1-dev xvfb firefox libjpeg-dev

# Copy script to run services at boot like memcached, etc.
RUN mkdir -p /etc/my_init.d
ADD bin/docker/services.sh /etc/my_init.d/services.sh

RUN mkdir /airmozilla
ADD requirements.txt /airmozilla/
WORKDIR /airmozilla

# Install python dependencies.
RUN pip install -r requirements.txt

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
