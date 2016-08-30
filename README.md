===========================
ganeti-extstorage-dataontap
===========================

External storage provider for Netapp's Data ONTAP Systems

### Installation

* Using Debian jessie packages:
```bash
echo "deb http://apt.dev.grnet.gr jessie/" > /etc/apt/sources.list.d/apt.dev.grnet.gr.list
wget --no-check-certificate  -qO-  http://dev.grnet.gr/files/apt-grnetdev.pub | apt-key add -
apt-get update
apt-get install ganeti-exstorage-dataontap
```

* From source:
```bash
git clone https://github.com/grnet/ganeti-extstorage-dataontap.git
cd ganeti-extstorage-dataontap
python setup.py --install-scripts=/usr/share/ganeti/extstorage
mkdir -p /etc/ganeti
sed 's/^[A-Z \t]/# \0/g' extstorage_dataontap/configuration/default.py > /etc/ganeti/extstorage-dataontap.conf
mkdir -p /etc/ganeti/hooks/instance-{migrate,failover}-pre.d
ln -s /usr/share/ganeti/extstorage/dataontap/pre-migrate /etc/ganeti/hooks/instance-migrate-pre.d/extstorage-dataontap
ln -s /usr/share/ganeti/extstorage/dataontap/pre-failover /etc/ganeti/hooks/instance-failover-pre.d/extstorage-dataontap
mkdir -p /etc/ganeti/hooks/instance-remove-post.d
ln -s /usr/share/ganeti/extstorage/dataontap/post-remove /etc/ganeti/hooks/instance-remove-post.d/extstorage-dataontap
```

### Configure

Just edit `/etc/ganeti/extstorage-dataontap.conf`

