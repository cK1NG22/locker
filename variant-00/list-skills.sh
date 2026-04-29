#!/bin/sh
curl -s -H "X-API-Key: mykey" http://localhost:8080/api/v1/skills | python3 -m json.tool
