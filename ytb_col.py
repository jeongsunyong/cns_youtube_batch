# encoding=utf8

import time
import json
import requests
from elasticsearch import Elasticsearch,helpers
from datetime import datetime
import sys
import re

from hanspell import spell_checker
from konlpy.tag import Okt, Mecab
from collections import Counter

import warnings
 
warnings.filterwarnings("ignore")

#es=Elasticsearch('http://localhost:9200')
#es=Elasticsearch(hosts='http://172.21.0.1:9200',verify_certs=False,headers={"Content-Type" : "application/json"})
es=Elasticsearch(hosts='https://sunyong:New1234!@search-ytb-intern-es-ptazwbixw6haqglce4347n6n6e.ap-northeast-2.es.amazonaws.com/',verify_certs=False,headers={"Content-Type" : "application/json"})

def getConfig() : # api key 조회 함
    index="youtube_config"
    res=''
    try:
        body={
            "query":{
                "match_all":{}
            }
        }
        res=es.search(index=index, body=body)

        if len(res['hits']['hits']) <= 0:
            #print(res)
            print(f"no data error")
            return False

        base_url=res['hits']['hits'][0]['_source']['url']
        api_key=res['hits']['hits'][0]['_source']['api_key']
        max_vid=res['hits']['hits'][0]['_source']['max_video_num']
        max_com=res['hits']['hits'][0]['_source']['max_comment_num']

        return base_url,api_key,max_vid,max_com
    except Exception as e:
        print(e)

def getProducts(): # 사용자가 지정한 제품들의 리스트 조회
    index="products"
    res=''
    try:
        body = {
            "query":{
                "match_all":{}
            }
        }
        res=es.search(index=index,body=body)

        if len(res['hits']['hits'])<=0:
            print(res)
            print(f"no data error")
            return False

        products_info=res['hits']['hits']
        return products_info

    except Exception as e:
        print(e)

def youtubeProductSearch(base_url,api_key,max_vid,max_com,search):
    
    videos=[] # youtube video 저장 

    req_url=f"{base_url}/search?part=snippet&regionCode=KR&maxResults=5&order=viewCount&key={api_key}&q='{search}'"
    try:
        res=requests.get(req_url)
        vid_res=res.json()['items']
        for vid in vid_res:
            content_schema={
                'content_id':'',
                'title':'',
                'img_url':'',
                'views':'',
                'likes':'',
                'date':'',
                'keywords':{
                    'rank1':{},
                    'rank2':{},
                    'rank3':{},
                    'rank4':{},
                    'rank5':{}
                }
            }

            id_v=vid['id']['videoId']
            req_url_vid=f"{base_url}/videos?key={api_key}&id={id_v}&part=snippet,statistics"
            res_v=requests.get(req_url_vid).json()
            item=res_v['items'][0]
            content_schema['content_id']=id_v
            content_schema['title']=item['snippet']['title']
            content_schema['img_url']=item['snippet']['thumbnails']['high']['url']
            content_schema['date']=item['snippet']['publishedAt']
            content_schema['views']=item['statistics']['viewCount']
            content_schema['likes']=item['statistics']['likeCount']
            videos.append(dict(content_schema))

        return videos

        
    except Exception as e:
        print(e)


def getStopwords():
    index="stopwords"
    res=''
    try:
        body = {
            "query":{
                "match_all":{}
            },
            "size":1000
        }
        res=es.search(index=index,body=body)
        if len(res['hits']['hits'])<=0:
            #print(res)
            return False
            
        stopwords_sources=res['hits']['hits']

        stopwords=[]
        for s in stopwords_sources:
            stopword=s['_source']['stopword']
            stopwords.append(stopword)
        return stopwords

    except Exception as e:
        print(e)



if __name__=="__main__":
    print(f"[{time.strftime('%H:%M:%S')}] : process start")

    #1. get product info
    print(f"[{time.strftime('%H:%M:%S')}] : get all product info start")
    products = getProducts()
    print(f"[{time.strftime('%H:%M:%S')}] : get all product info finished")

    #2. get youtube api
    print(f"[{time.strftime('%H:%M:%S')}] : get youtube api config start")
    base_url,api_key,max_vid,max_com=getConfig()
    print(f"[{time.strftime('%H:%M:%S')}] : get youtube api config finished")
    
    #3. youtube product search
    print(f"[{time.strftime('%H:%M:%S')}] : search youtube product start")
    video_by_product=dict()
    for product_source in products:
        product=product_source['_source']['product_name']
        product_id=product_source['_source']['product_id']
        videos = youtubeProductSearch(base_url,api_key,max_vid,max_com,product)
        video_by_product[product_id]=videos
        #print(videos)
    print(f"[{time.strftime('%H:%M:%S')}] : search youtube product finished")

    #vid-product-map
    vid_product_map=dict()
    for product_id in video_by_product:
        for video in video_by_product[product_id]:
            vid=video['content_id']
            vid_product_map[vid]=product_id
    #print(vid_product_map)

    print(f"[{time.strftime('%H:%M:%S')}] : comments collecting start")
    
    vid_comments=dict() # video별 comments
    for product_id in video_by_product:
        print(f"product_id : {product_id}")
        videos = video_by_product[product_id]
        v_list = [item['content_id'] for item in videos]

        #comment thread 수집 
        for vid in v_list:
            vid_comments[vid]=[]
            cnt=0
            page_token=''
            while page_token != '' or cnt==0:
                cnt+=1
                com_url=f"{base_url}/commentThreads?part=replies&maxResult=50&videoId={vid}&key={api_key}&pageToken={page_token}"
                com_res=requests.get(com_url).json()
                for item in com_res['items']:
                    vid_comments[vid].append(item['id'])
                if 'nextPageToken' not in com_res or cnt>20 :
                    break
                page_token=com_res['nextPageToken']

    # comment 내용 수집
    vid_com_list=dict()
    for vid in vid_comments:
        print(f" vid com list : {vid}")
        vid_com_list[vid]=[]
        for com_id in vid_comments[vid]:
            comment_url=f"{base_url}/comments?textFormat=plainText&part=snippet&id={com_id}&key={api_key}"
            com_res=requests.get(comment_url)
            #print(com_res)
            try:
                vid_com_list[vid].append(com_res.json()['items'])
            except Exception as e:
                
                print("-")
                #print(e)
                #print(vid_com_list)
                #print(com_res)

    data_by_vid=dict()
    for vid in vid_com_list:
        data_by_vid[vid]=[]
        for com_res in vid_com_list[vid]:
            for element in com_res:
                comment_id=element['id']
                comment=element['snippet']
                com_text=comment['textDisplay']
                com_like=comment['likeCount']
                com_date=comment['updatedAt']
                data_by_vid[vid].append({
                    'com_id':comment_id,
                    'com_text':re.sub(r"[^A-Za-z0-9가-힣 ]","",com_text).upper(), # cleansing :  특문제거
                    "com_original":com_text,
                    'com_like':com_like,
                    'com_date':com_date
                })

    print(f"[{time.strftime('%H:%M:%S')}] : comments collecting finished")
    
    stopwords=getStopwords()

    tokenizer=Mecab()
    words_by_vid=dict()
    total_words=[]
    for vid in data_by_vid:
        words_by_vid[vid]=[]
        print(f"###################################{vid}")
        words=[]
        data=data_by_vid[vid]
        for comment in data:
            try: 
                spell_check=spell_checker.check(comment['com_text']) # 맞춤법 cleansing
                text=spell_check.checked
                tokens=tokenizer.nouns(text) # tokenizing : 명사 keyword만 뽑아내기
                comment['com_token']=tokens
                comment['com_text']=text
                for token in tokens:
                    words.append(token)
                    total_words.append(token)
            except Exception as e:
                print(e)
                #print(f"err {comment}")

        counter = Counter(words)
        valids=[]

        for valid in filter(lambda word: word not in stopwords,counter):
            valids.append([valid,counter[valid]])

        valids.sort(key=lambda x:-x[1])
        candidates=valids[0:5]

        #print(candidates)
        product_id=vid_product_map[vid]
        for video in video_by_product[product_id]:
            if video['content_id']==vid:
                video['keywords']['rank1']['token']=candidates[0][0]
                video['keywords']['rank1']['cnt']=candidates[0][1]
                video['keywords']['rank2']['token']=candidates[1][0]
                video['keywords']['rank2']['cnt']=candidates[1][1]
                video['keywords']['rank3']['token']=candidates[2][0]
                video['keywords']['rank3']['cnt']=candidates[2][1]

    
        words_by_vid[vid]=list(words)

    print(video_by_product) # video 저장할 것
    bulk_actions=[]
    for product_id in video_by_product:
        print(f"product_id : {product_id}")
        for video in video_by_product[product_id]:
            video['product_id']=product_id
            bulk_actions.append({
                '_op_type':'update',
                '_index':'youtube_contents',
                '_id':video['content_id'],
                'doc':dict(video),
                'doc_as_upsert':True
            })

    try: 
        helpers.bulk(es,bulk_actions)
        #print(bulk_actions)
    except Exception as e:
        print(e)

    # comment 저장할 것
    for vid in data_by_vid:
        bulk_actions=[]
        data=data_by_vid[vid]
        print(f"vid : {vid} data length : {len(data)}")
        for comment in data:
            bulk_actions.append({
                '_op_type':'update',
                '_index':'youtube_comments',
                '_id':comment['com_id'],
                'doc':{
                    'content_id':vid,
                    'comment':comment['com_text'],
                    'original':comment['com_original'],
                    'tokens':[{'token':token} for token in comment['com_token']],
                    'date':comment['com_date'],
                    'like':comment['com_like'],
                },
                'doc_as_upsert':True
            })
        try:
            helpers.bulk(es,bulk_actions)
            #print(bulk_actions)
        except Exception as e:
            print(e)
    
    
    print(f"----data save . . .")
    #print(words_by_vid)

    # video
        # keyword 추가하면 됨. (rank에 따라 keyword, token) -> product에 저장 
    # comments
        # video에 따라 저장되있으며 text,original,like,data포함하여 저장
