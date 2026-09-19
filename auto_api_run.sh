#!/bin/bash


echo "step 1: check if it is running"
ps -ef |grep "python3 run_api_cases.py" |grep -v grep
if [ $? -eq 0 ]; then
     echo "Api automation is running, kill it"
     ps -ef |grep "python3 run_api_cases.py" |grep -v grep |awk '{print $2}' |xargs kill -9
     # exit 2
else
     echo "Api automation not running, start it"
fi

echo "step 2: start git fetch"
# CUR_DIR='/home/ubuntu/TM-Automation-Tests/API_Automation_PY3/'
CUR_DIR=$(cd "$(dirname "$0")"; pwd)
echo ${CUR_DIR}
cd ${CUR_DIR}
# git pull
git fetch --all
git reset --hard origin/PROD
git switch PROD
echo "git pull completed."

echo "step 3: sync .yaml file from s3"
cd ${CUR_DIR}
date
pip3 install -U -r requirement.txt
python3 -m pip install -U pip
cd ${CUR_DIR}/config/
aws s3 cp s3://htm-test/TM-Automation-Tests/API_Automation_PY3/config/config.yaml config.yaml
if [ $? -eq 0 ]; then
    echo "cp config.yaml from aws s3 succeed"
else
    echo "cp config.yaml from aws s3 failed"
    if [ -f config-mod.yaml ]; then
        cp config-mod.yaml config.yaml
    else
        echo 'config-mod.yaml file not exists'
    fi
fi

echo "step 4: run api automation py3 script"
cd ${CUR_DIR}
date
python3 run_api_cases.py $1

echo "step 5: back report_xml data and delete too old log/report files"
# cd ${CUR_DIR}/report
# DATE_MIN=$(date +%Y%m%d-%H%M)
# tar -czf report_xml_${DATE_MIN}.tar.gz xml/


echo "delete logs/backed reports files which older than 15 day"
find ${CUR_DIR}/logs/ -maxdepth 2 -mtime +15 -type d |xargs rm -rf
find ${CUR_DIR}/report/ -maxdepth 2 -mtime +15 -type d |xargs rm -rf
echo "delete too old reports html files"
find /home/ubuntu/www/allure_html_api -maxdepth 2 -mtime +31 -type d | xargs rm -rf
find /home/ubuntu/www/report -maxdepth 2 -mtime +31 -type f | xargs rm -f
find /home/ubuntu/www/report_api_issue -maxdepth 2 -mtime +31 -type f | xargs rm -f
# aws s3 sync logs s3://htm-test/wangjian/logs --delete
date
echo 'Done'

