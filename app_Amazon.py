import numpy as np
import pandas as pd
import time
from redis.commands.search.field import VectorField
from redis.commands.search.field import TextField
from redis.commands.search.field import TagField
from redis.commands.search.query import Query
import redis

MAX_TEXT_LENGTH=512
NUMBER_PRODUCTS=1000

def auto_truncate(val):
    return val[:MAX_TEXT_LENGTH]

#Load Product data and truncate long text fields
all_prods_df = pd.read_csv("product_data.csv", converters={'bullet_point': auto_truncate,'item_keywords':auto_truncate,'item_name':auto_truncate})
all_prods_df['primary_key'] = all_prods_df['item_id'] + '-' + all_prods_df['domain_name']
all_prods_df['item_keywords'].replace('', np.nan, inplace=True)
all_prods_df.dropna(subset=['item_keywords'], inplace=True)
all_prods_df.reset_index(drop=True,inplace=True)

#get the first 1000 products with non-empty item keywords
product_metadata = all_prods_df.head(NUMBER_PRODUCTS).to_dict(orient='index')

all_prods_df.head()

def load_vectors(client, product_metadata, vector_dict, vector_field_name):
    p = client.pipeline(transaction=False)
    for index in product_metadata.keys():    
        #hash key
        key='product:'+ str(index)+ ':' + product_metadata[index]['primary_key']
        
        #hash values
        item_metadata = product_metadata[index]
        item_keywords_vector = vector_dict[index].astype(np.float32).tobytes()
        item_metadata[vector_field_name]=item_keywords_vector
        
        # HSET
        p.hset(key,mapping=item_metadata)
            
    p.execute()

def create_flat_index (redis_conn,vector_field_name,number_of_vectors, vector_dimensions=512, distance_metric='L2'):
    redis_conn.ft().create_index([
        VectorField(vector_field_name, "FLAT", {"TYPE": "FLOAT32", "DIM": vector_dimensions, "DISTANCE_METRIC": distance_metric, "INITIAL_CAP": number_of_vectors, "BLOCK_SIZE":number_of_vectors }),
        TagField("product_type"),
        TextField("item_name"),
        TextField("item_keywords"),
        TagField("country")        
    ]) 

    ITEM_KEYWORD_EMBEDDING_FIELD='item_keyword_vector'
TEXT_EMBEDDING_DIMENSION=768
NUMBER_PRODUCTS=1000

print ('Loading and Indexing + ' +  str(NUMBER_PRODUCTS) + ' products')

#flush all data
redis_conn.flushall()

#create flat index & load vectors
create_flat_index(redis_conn, ITEM_KEYWORD_EMBEDDING_FIELD,NUMBER_PRODUCTS,TEXT_EMBEDDING_DIMENSION,'COSINE')
load_vectors(redis_conn,product_metadata,item_keywords_vectors,ITEM_KEYWORD_EMBEDDING_FIELD)