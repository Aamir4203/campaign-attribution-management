source /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/REQUEST_PROCESSING/$1/ETC/config.properties
source $TRACKING_HELPER

append_process_id $REQUEST_ID "RESP"


echo "MODULE2 Start Time: `date`"


#==== ERROR FUNCTION ===#

error_fun()
{

    $CONNECTION_STRING -vv -c "update $REQUEST_TABLE set REQUEST_STATUS='E',ERROR_CODE=$1  ,request_end_time=now(), REQUEST_DESC=concat(REQUEST_DESC,'- ','$2') where REQUEST_ID=$REQUEST_ID"

}


CREATIVE_ID=` $CONNECTION_STRING -qtAX -c "select DISTINCT trim(CREATIVEID)  from $REPORT_TABLE  " `

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to fetch cretives from report table."
        exit

fi


OFFERIDS=`$CONNECTION_STRING -qtAX -c "select DISTINCT trim(OFFERID)   from $REPORT_TABLE  " `

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to fetch offerids from report table."
        exit

fi


RANGE=`$CONNECTION_STRING -qtAX -F',' -c "select max(del_date),min(del_date)  from $REPORT_TABLE  " `

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to fetch max-min of deldate from report table."
        exit

fi


IFS=$',' read -r max_date_1 min_date <<< "$RANGE"

max_date=`date -d "$max_date_1 1 days" +%Y-%m-%d`

formatted_max_date=$(echo "$max_date" | sed 's/-//g')
formatted_min_date=$(echo "$min_date" | sed 's/-//g')


creatives=`echo $CREATIVE_ID | sed "s/\b\([0-9]\+\)\b/'\1'/g"|tr ' ' ','`

offers=`echo $OFFERIDS |sed "s/\b\([0-9]\+\)\b/'\1'/g"|tr ' ' ','`

orange_cake_offids=`$CONNECTION_STRING -qtAX -c "select DISTINCT trim(OFFERID)   from $REPORT_TABLE  "  | tr '\n' ',' | sed "s/,$//g" `



#=== Green Delivered ===#


$SF_STRING -q "SELECT DISTINCT TOADDRESS,TO_CHAR(TO_DATE(TIMELOGGED_DATE, 'YYYYMMDD'), 'YYYY-MM-DD') DEL_DATE,SUBID,BOUNCECAT FROM GREEN.LIST_PROCESSING.PMTA_LOG_SUMMARY_ACTIVE_HISTORICAL WHERE OFFERID IN ($offers) AND TIMELOGGED_DATE BETWEEN '$formatted_min_date' and '$formatted_max_date' and (BOUNCECAT='success' or DELIVEREDSTATUS='Hard Bounce') and  REGEXP_LIKE(listId, '^[0-9]+$') and type in ('d','b') and BOUNCECAT  ;" -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'   >$SPOOLPATH/delivered


if [[ $? -ne 0 ]]
then

        sleep 5s

        $SF_STRING -q "SELECT DISTINCT TOADDRESS,TO_CHAR(TO_DATE(TIMELOGGED_DATE, 'YYYYMMDD'), 'YYYY-MM-DD') DEL_DATE,SUBID,BOUNCECAT FROM GREEN.LIST_PROCESSING.PMTA_LOG_SUMMARY_ACTIVE_HISTORICAL WHERE OFFERID IN ($offers) AND TIMELOGGED_DATE BETWEEN '$formatted_min_date' and '$formatted_max_date' and (BOUNCECAT='success' or DELIVEREDSTATUS='Hard Bounce')  ;" -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'   >$SPOOLPATH/delivered


        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to fetch delivered data from impala table."
                exit

        fi
fi



$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_DELIVERED_TEMP "
$CONNECTION_STRING -vv -c "create table $GREEN_DELIVERED_TEMP (ID SERIAL,email  varchar ,del_date varchar,subid varchar,bouncecat varchar) "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create Green delivered table."
        exit

fi

$CONNECTION_STRING -vv -c "\copy $GREEN_DELIVERED_TEMP(email,del_date,subid,bouncecat)  from '$SPOOLPATH/delivered' with delimiter '|' header csv "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to load Green delivered data into table."
        exit

fi


#=== Green opens ===#

$SF_STRING -q "select distinct EMAILID,OPENDATE,SUBID from GREEN.GREEN_LPT.RAW_OPENS_FOLLOWUP where OPENDATE>='$min_date' and OFFERID in ($offers);" -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'  >$SPOOLPATH/opens

if [[ $? -ne 0 ]]
then

        sleep 5s

        $SF_STRING -q "select distinct EMAILID,OPENDATE,SUBID from GREEN.GREEN_LPT.RAW_OPENS_FOLLOWUP where OPENDATE>='$min_date' and OFFERID in ($offers);" -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'  >$SPOOLPATH/opens


        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to fetch green opens from impala table."
                exit

        fi


fi



$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_OPENS_TEMP "
$CONNECTION_STRING -vv -c "create table $GREEN_OPENS_TEMP (id SERIAL ,email  varchar ,OPEN_DATE varchar,subid varchar) "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create Green Opens table."
        exit

fi


$CONNECTION_STRING -vv -c "\copy $GREEN_OPENS_TEMP(email,OPEN_DATE,subid)  from '$SPOOLPATH/opens' with delimiter '|' header csv "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to load Green Opens data into table."
        exit

fi



#=== Green clicks ===#


$SF_STRING -q "select distinct EMAILID,CLICKDATE,SUBID from GREEN.LIST_PROCESSING.RAW_CLICKS_FOLLOWUP_SF where CLICKDATE>='$min_date' and OFFERID in ($offers);" -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'  >$SPOOLPATH/clicks

if [[ $? -ne 0 ]]
then

        sleep 5s

        $SF_STRING -q "select distinct EMAILID,CLICKDATE,SUBID from GREEN.LIST_PROCESSING.RAW_CLICKS_FOLLOWUP_SF where CLICKDATE>='$min_date' and OFFERID in ($offers);" -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'  >$SPOOLPATH/clicks


        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to pull green clicks from impala table"

        fi

fi

$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_CLICKS_TEMP "
$CONNECTION_STRING -vv -c "create table $GREEN_CLICKS_TEMP (id SERIAL ,email  varchar ,CLICK_DATE varchar,subid varchar) "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create Green Clicks table."
        exit

fi



$CONNECTION_STRING -vv -c "\copy $GREEN_CLICKS_TEMP(email,CLICK_DATE,subid)  from '$SPOOLPATH/clicks' with delimiter '|' header csv "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to load  Green Clicks data into table."
        exit

fi


#==== GREEN ALL UNSUBS ===#


$SF_STRING -q "select distinct email from GREEN.LIST_PROCESSING.APT_UNSUB_DETAILS_SF where  offerid in ($offers) and LASTUNSUBDATE<'$min_date' "  -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'   > $SPOOLPATH/green_all_unsubs

if [[ $? -ne 0 ]]
then

        sleep 5s

        $SF_STRING -q "select distinct email from GREEN.LIST_PROCESSING.APT_UNSUB_DETAILS_SF where  offerid in ($offers) and LASTUNSUBDATE<'$min_date'"  -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false  | tr ',' '|' | sed 's/"//g'   > $SPOOLPATH/green_all_unsubs

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to pull green unsubs  from impala table"

        fi

fi



$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_TOTAL_UNSUBS_TEMP  "

$CONNECTION_STRING -vv -c "create table $GREEN_TOTAL_UNSUBS_TEMP (email  varchar unique) "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create Green Unsubs table."
        exit

fi

$CONNECTION_STRING -vv -c "copy $GREEN_TOTAL_UNSUBS_TEMP(email)  from '$SPOOLPATH/green_all_unsubs' with delimiter '|' header csv "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to load data into Green Unsubs table."
        exit

fi

#tmp_indx_name="gr_tmp_idx_$REQUEST_ID"
#
#$CONNECTION_STRING -vv -c "create index $tmp_indx_name on $GREEN_TOTAL_UNSUBS_TEMP(UNSUB_DATE)"

#=== Green Unsubs ===#

$SF_STRING -q "select email,to_date(LASTUNSUBDATE),subid from GREEN.LIST_PROCESSING.APT_UNSUB_DETAILS_SF where  offerid in ($offers) and to_date(LASTUNSUBDATE)>='$min_date' " -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false | tr '\t' '|' > $SPOOLPATH/unsubs

if [[ $? -ne 0 ]]
then

        sleep 5s

        $SF_STRING -q "select email,to_date(LASTUNSUBDATE),subid from GREEN.LIST_PROCESSING.APT_UNSUB_DETAILS_SF where  offerid in ($offers) and to_date(LASTUNSUBDATE)>='$min_date' " -o output_format=csv -o header=true -o timing=false -o friendly=false -o variable_substitution=false | tr '\t' '|' > $SPOOLPATH/unsubs

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to pull green unsubs from impala table"

        fi

fi



$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_UNSUBS_TEMP "
$CONNECTION_STRING -vv -c "create table $GREEN_UNSUBS_TEMP (id SERIAL ,email  varchar ,UNSUB_DATE varchar,subid varchar) "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create Green Unsubs table."
        exit

fi

$CONNECTION_STRING -vv -c "\copy $GREEN_UNSUBS_TEMP(email,UNSUB_DATE,subid)  from '$SPOOLPATH/unsubs' with delimiter '|' header csv "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to load data into Green Unsubs table."
        exit

fi




#====== final table ===#


$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_FINAL_TEMP "
$CONNECTION_STRING -vv -c "CREATE TABLE $GREEN_FINAL_TEMP(EMAIL VARCHAR,DEL_DATE VARCHAR ,OPEN_DATE VARCHAR,CLICK_DATE VARCHAR,UNSUB_DATE VARCHAR, STATUS INT DEFAULT 1 , SUBID VARCHAR, UNSUB INT DEFAULT 0,unique(email,del_date))"

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create Green Final Delivered table."
        exit

fi

$CONNECTION_STRING -vv -c "create index subid_index_final_$REQUEST_ID  on $GREEN_FINAL_TEMP( SUBID)"

#=== BOUNCES INSERT ===#

#$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,DEL_DATE,STATUS) SELECT EMAIL,DEL_DATE,-1 FROM $GREEN_DELIVERED_TEMP where bouncecat <> ('success')  ON CONFLICT DO NOTHING"

#if [[ $? -ne 0 ]]
#then
#
#        error_fun "2" "Unable to insert  Green Bounces into Final Green Delivered table."
#        exit
#
#fi


#=== UNSUBS INSERT ===#

$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,DEL_DATE,OPEN_DATE,UNSUB_DATE,STATUS,SUBID,UNSUB) SELECT A.EMAIL,B.DEL_DATE,A.UNSUB_DATE,A.UNSUB_DATE,2,A.SUBID,1 FROM $GREEN_UNSUBS_TEMP A , $GREEN_DELIVERED_TEMP B WHERE A.EMAIL=B.EMAIL AND A.SUBID=B.SUBID and A.EMAIL=B.EMAIL ON CONFLICT DO NOTHING"

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert  Green Unsubs into Final Green Delivered table."
        exit

fi

#$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,OPEN_DATE,UNSUB_DATE,STATUS,SUBID,UNSUB) SELECT A.EMAIL,A.UNSUB_DATE,A.UNSUB_DATE,2,A.SUBID,1 FROM $GREEN_UNSUBS_TEMP A  ON CONFLICT DO NOTHING"


 #=== CLICKS INSERT ===#

$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,STATUS,SUBID) SELECT A.EMAIL,B.DEL_DATE,A.CLICK_DATE,A.CLICK_DATE,3,A.SUBID FROM $GREEN_CLICKS_TEMP A ,  $GREEN_DELIVERED_TEMP B WHERE A.EMAIL=B.EMAIL AND A.SUBID=B.SUBID ON CONFLICT DO NOTHING"

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert  Green Clicks into Final Green Delivered table."
        exit

fi

#$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,OPEN_DATE,CLICK_DATE,STATUS,SUBID) SELECT A.EMAIL,A.CLICK_DATE,A.CLICK_DATE,3,A.SUBID FROM $GREEN_CLICKS_TEMP A  ON CONFLICT DO NOTHING"



#==== OPENS INSERT ===#

$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,DEL_DATE,OPEN_DATE,STATUS,SUBID) SELECT A.EMAIL,B.DEL_DATE,A.OPEN_DATE,2,A.SUBID FROM $GREEN_OPENS_TEMP A ,  $GREEN_DELIVERED_TEMP B WHERE A.EMAIL=B.EMAIL AND A.SUBID=B.SUBID ON CONFLICT DO NOTHING"

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert  Green Opens into Final Green Delivered table."
        exit

fi

#$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,OPEN_DATE,STATUS,SUBID) SELECT A.EMAIL,A.OPEN_DATE,2,A.SUBID FROM $GREEN_OPENS_TEMP A ON CONFLICT DO NOTHING"



#=== DELIVERED INSERT ===#

$CONNECTION_STRING -vv -c " INSERT INTO $GREEN_FINAL_TEMP (EMAIL,DEL_DATE,STATUS,SUBID) SELECT EMAIL,DEL_DATE,1,SUBID FROM  $GREEN_DELIVERED_TEMP ON CONFLICT DO NOTHING"

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert  Green Delivered into Final Green Delivered table."
                exit

fi

#================================================== FINAL INSERT ===#


$CONNECTION_STRING -vv -c "CREATE TABLE $UNIQ_GEN_TABLE(EMAIL VARCHAR ,DEL_DATE VARCHAR ,OPEN_DATE VARCHAR,CLICK_DATE VARCHAR,UNSUB_DATE VARCHAR, STATUS INT DEFAULT 1 , SUBID VARCHAR, UNSUB INT DEFAULT 0,CHANNEL VARCHAR,unique(email,del_date) )"


if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create genuine delivered table"
                exit

fi

$CONNECTION_STRING -vv -c " INSERT INTO $UNIQ_GEN_TABLE (EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,UNSUB_DATE,STATUS,SUBID,UNSUB,CHANNEL) SELECT  EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,UNSUB_DATE,STATUS,SUBID,UNSUB,'Green' FROM  $GREEN_FINAL_TEMP ON CONFLICT DO NOTHING"

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert green genuine delivered data into final table"
                exit

fi



$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $GREEN_DELIVERED_TEMP , $GREEN_OPENS_TEMP , $GREEN_CLICKS_TEMP , $GREEN_UNSUBS_TEMP , $GREEN_FINAL_TEMP "



#========================== ARCAMAX DATA PULLING ==========#

$PGDB2_CONN_STRING -vv -c "DROP table IF EXISTS  $ARCA_GENUINE_DEL_TEMP"

$PGDB2_CONN_STRING -vv -c "create table $ARCA_GENUINE_DEL_TEMP (email varchar ,del_date varchar,open_date varchar, click_date varchar,status int default 1,creative_id varchar,unsub int default 0) "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create arcamax delivered table in pgdb2 "
                exit

fi


$PGDB2_CONN_STRING -vv -c "insert into $ARCA_GENUINE_DEL_TEMP (email,del_date,open_date,click_date,creative_id,status) select email,del_date,open_date,click_date,ad_creative_id,(case when click_date is not null then '3' when open_date is not null then '2' else 1 end) status from apt_custom_arcamax_responders_dnd where ad_creative_id in ($creatives) and del_date>='$min_date' and del_date<='$max_date' "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert into arcamax delivered table in pgdb2 from arca resp table "
                exit

fi


$PGDB2_CONN_STRING -vv -c "insert into $ARCA_GENUINE_DEL_TEMP (email,del_date,creative_id) select email,del_date,ad_creative_id from apt_custom_arcamax_delivered_dnd where ad_creative_id in ($creatives) and  del_date>='$min_date' and del_date<='$max_date'   "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert into arcamax delivered table in pgdb2 from arca del table "
                exit

fi


$PGDB2_CONN_STRING -qtAX -c "select email,del_date,open_date,click_date,status from $ARCA_GENUINE_DEL_TEMP  order by status desc " > $SPOOLPATH/arca_max_genuine

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to write delivered data to file from pgdb2"
                exit

fi

$PGDB2_CONN_STRING -vv-c "drop table $ARCA_GENUINE_DEL_TEMP "

$CONNECTION_STRING -vv -c " create table $ARCA_GENUINE_DEL_TEMP (email varchar ,del_date varchar,open_date varchar, click_date varchar,status int default 1) "


if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to create arca delivered table in apt_tool_db"
                exit

fi



$CONNECTION_STRING -vv -c "\copy $ARCA_GENUINE_DEL_TEMP  FROM '$SPOOLPATH/arca_max_genuine' with delimiter '|'  "

if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to load arca delivered data into table in apt_tool_db"
                exit

fi

#========= ALL CHANNELS FINAL UNIQUE GEN TABLE ====#


$CONNECTION_STRING -vv -c " INSERT INTO $UNIQ_GEN_TABLE (EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,STATUS,CHANNEL) SELECT  EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,STATUS,'Arcamax' FROM  $ARCA_GENUINE_DEL_TEMP order by status desc ON CONFLICT DO NOTHING"


if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert arca genuine delivered data into final table"
                exit

fi


$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $ARCA_GENUINE_DEL_TEMP "


#=====================================ORANGE DATA PULLING =========================================#

orange_offerids=`$ORANGE_STRING -A -ss -e "Select distinct offer_id from mt_offer_cake_offer_mappings where cake_offer_id in ($orange_cake_offids) " | tr '\n' ',' | sed "s/,$//g" `


if [[ $? -ne 0 ]]
then

        sleep 5s

            orange_offerids=`$ORANGE_STRING -A -ss -e "Select distinct offer_id from mt_offer_cake_offer_mappings where cake_offer_id in ($orange_cake_offids) " | tr '\n' ',' | sed "s/,$//g" `


                if [[ $? -ne 0 ]]
                then

                        error_fun "2" "Unable to pull offerids for orange"
                        exit
                fi

fi


$ORANGE_STRING -A -ss -e "select id,send_date from deploys where offer_id in ($orange_offerids) and send_date between '$min_date' and '$max_date' "|sed 's/\t/|/g' > $SPOOLPATH/deployids.txt

if [[ $? -ne 0 ]]
then

        sleep 5s

        $ORANGE_STRING -A -ss -e "select id,send_date from deploys where offer_id in ($orange_offerids) and send_date between '$min_date' and '$max_date' "|sed 's/\t/|/g' > $SPOOLPATH/deployids.txt

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to pull orange deploy ids"

        fi

fi

deployids=`cat $SPOOLPATH/deployids.txt |cut -d'|' -f1 | sed  ':a;N;$!ba;s/\n/,/g' `

echo $deployids

if [[ $deployids != "" ]]
then

        $CONNECTION_STRING -vv -c "DROP table IF EXISTS  $ORANGE_DEPLOY_IDS_TABLE"

        $CONNECTION_STRING -vv -c "create table $ORANGE_DEPLOY_IDS_TABLE (deploy_id varchar ,sent_date varchar  ) "

        $CONNECTION_STRING -vv -c "\copy $ORANGE_DEPLOY_IDS_TABLE(deploy_id,sent_date)  from '$SPOOLPATH/deployids.txt' with delimiter '|' header csv "


        #==== RESPONDERS ===#

        $ORANGE_STRING -A -ss -e "select  b.email_address,date(action_datetime),a.action_id,sub_aff_id From content_server_stats_raws a join emails b on a.eid=b.id  where a.id>3856934224  and sub_aff_id in ($deployids)  "|sed 's/\t/|/g' >  $SPOOLPATH/Orange_delivered

        $ORANGE_STRING -A -ss -e "select  b.email_address,date(action_datetime),a.action_id,sub_aff_id  From content_server_stats_raws a join first_party_feed_emails  b on a.eid=b.id  where a.id>3856934224  and sub_aff_id in ($deployids) "|sed 's/\t/|/g' >> $SPOOLPATH/Orange_delivered

        $ORANGE_STRING -A -ss -e "select email_address,date(datetime),action_id,deploy_id from mt2_reports.email_actions a join mt2_data.first_party_feed_emails b on a.email_id = b.id where deploy_id in ($deployids)  and datetime > '$min_date 00:00:00' and datetime < '$max_date 00:00:00' "|sed 's/\t/|/g' >> $SPOOLPATH/Orange_delivered

        #====================#

        $CONNECTION_STRING -vv -c "DROP table IF EXISTS  $ORANGE_GENUINE_DEL_TEMP"

        $CONNECTION_STRING -vv -c "create table $ORANGE_GENUINE_DEL_TEMP (email varchar ,date_ varchar,STATUS INT,deploy_id varchar  ) "

        $CONNECTION_STRING -vv -c "\copy $ORANGE_GENUINE_DEL_TEMP(email,date_,STATUS,deploy_id)  from '$SPOOLPATH/Orange_delivered' with delimiter '|' header csv "

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to load orange resp data into Orange table."
                exit

        fi

        #===== FINAL ORANGE DELIVERED TABLE ====#

        $CONNECTION_STRING -vv -c "DROP table IF EXISTS  $ORANGE_GENUNIE_DELIVERED "
        $CONNECTION_STRING -vv -c "CREATE TABLE $ORANGE_GENUNIE_DELIVERED(EMAIL VARCHAR ,DEL_DATE VARCHAR ,OPEN_DATE VARCHAR,CLICK_DATE VARCHAR,UNSUB_DATE VARCHAR, STATUS INT DEFAULT 1 , SUBID VARCHAR, UNSUB INT DEFAULT 0,deploy_id varchar,unique(email,del_date))"

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to create Orange Final Delivered table."
                exit

        fi

        #=== BOUNCES INSERT ===#

        $CONNECTION_STRING -vv -c "INSERT INTO $ORANGE_GENUNIE_DELIVERED(EMAIL,STATUS,deploy_id) SELECT EMAIL,'-1',deploy_id from $ORANGE_GENUINE_DEL_TEMP where STATUS='10' on conflict do nothing"

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to insert bounces into orange final table."
                exit

        fi

        #=== UNSUBS INSERT ===#

        $CONNECTION_STRING -vv -c "INSERT INTO $ORANGE_GENUNIE_DELIVERED(EMAIL,OPEN_DATE,UNSUB_DATE,STATUS,UNSUB,deploy_id) SELECT EMAIL,date_,date_,2,1,deploy_id from $ORANGE_GENUINE_DEL_TEMP where STATUS='7' on conflict do nothing"

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to insert Unsubs into orange final table."
                exit

        fi

        #=== CLICKS INSERT ===#

        $CONNECTION_STRING -vv -c "INSERT INTO $ORANGE_GENUNIE_DELIVERED(EMAIL,OPEN_DATE,click_date,STATUS,deploy_id) SELECT EMAIL,date_,date_,3,deploy_id from $ORANGE_GENUINE_DEL_TEMP where STATUS='2' on conflict do nothing"

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to insert clicks into orange final table."
                exit

        fi

        #=== OPENS INSERT ===#

        $CONNECTION_STRING -vv -c "INSERT INTO $ORANGE_GENUNIE_DELIVERED(EMAIL,OPEN_DATE,STATUS,deploy_id) SELECT EMAIL,date_,2,deploy_id from $ORANGE_GENUINE_DEL_TEMP where STATUS='1' on conflict do nothing"

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to insert OPENS into orange final table."
                exit

        fi

        #=== DELIVERED INSERT ===#

        $CONNECTION_STRING -vv -c "INSERT INTO $ORANGE_GENUNIE_DELIVERED(EMAIL,deploy_id) SELECT EMAIL,deploy_id from $ORANGE_GENUINE_DEL_TEMP where STATUS=4 on conflict do nothing"

        if [[ $? -ne 0 ]]
        then

                error_fun "2" "Unable to insert delivered into orange final table."
                exit

        fi

        $CONNECTION_STRING -vv -c "Create Index deploy_idex_1 on $ORANGE_GENUNIE_DELIVERED(deploy_id) "
        $CONNECTION_STRING -vv -c "Create Index deploy_idex_2 on $ORANGE_DEPLOY_IDS_TABLE(deploy_id) "

        #=== UPDATE DELIVERED DATE  ===#

        $CONNECTION_STRING -vv -c "UPDATE $ORANGE_GENUNIE_DELIVERED a set del_date=sent_date from $ORANGE_DEPLOY_IDS_TABLE b where a.deploy_id=b.deploy_id "

        if [[ $? -ne 0 ]]
        then

                        error_fun "2" "Unable to UPDATE delivered date into final table"
                        exit

        fi

else

        $CONNECTION_STRING -vv -c "CREATE TABLE $ORANGE_GENUNIE_DELIVERED(EMAIL VARCHAR ,DEL_DATE VARCHAR ,OPEN_DATE VARCHAR,CLICK_DATE VARCHAR,UNSUB_DATE VARCHAR, STATUS INT DEFAULT 1 , SUBID VARCHAR, UNSUB INT DEFAULT 0,deploy_id varchar,unique(email,del_date))"

fi


$CONNECTION_STRING -vv -c " INSERT INTO $UNIQ_GEN_TABLE (EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,STATUS,CHANNEL) SELECT  EMAIL,DEL_DATE,OPEN_DATE,CLICK_DATE,STATUS,'Orange' FROM  $ORANGE_GENUNIE_DELIVERED order by status desc ON CONFLICT DO NOTHING"


if [[ $? -ne 0 ]]
then

        error_fun "2" "Unable to insert orange genuine delivered data into final table"
                exit

fi


$CONNECTION_STRING -vv -c "DROP table IF EXISTS  $ORANGE_GENUNIE_DELIVERED "
$CONNECTION_STRING -vv -c "DROP table IF EXISTS $ORANGE_DEPLOY_IDS_TABLE "
$CONNECTION_STRING -vv -c "DROP table IF EXISTS $ORANGE_GENUINE_DEL_TEMP "


#=== ADDING ROW NUMBER ===#

$CONNECTION_STRING -vv -c " alter table $UNIQ_GEN_TABLE add r_no int default 0, add id serial primary key "

$CONNECTION_STRING -vv -c " VACUUM FULL $UNIQ_GEN_TABLE "

$CONNECTION_STRING -vv -c "ANALYZE $UNIQ_GEN_TABLE "


$CONNECTION_STRING -vv -c "WITH cte AS (SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) AS row_number FROM $UNIQ_GEN_TABLE ) UPDATE $UNIQ_GEN_TABLE  SET r_no = cte.row_number FROM cte WHERE $UNIQ_GEN_TABLE.id=cte.id "



echo "MODULE2 End Time: `date`"


