#!/bin/sh

if curl http://localhost:9200/_cluster/health | grep -q '"cluster_name":"';
        then echo "Elasticsearch is running."
        else sudo systemctl start elasticsearch.service
        echo "Starting Elasticsearch."
fi
