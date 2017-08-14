# -*- coding: utf-8 -*-
"""
Created on Sun Jul 23 22:10:50 2017

@author: hxy
"""

# -*- coding: utf-8 -*-
"""
Created on Sun Jul 23 16:05:13 2017

@author: hxy
"""

# 本代码完成清理数据并将清理后的数据转成csv格式

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "beijing_china.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+',re.I)
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

mapping = {"jie":"Street","Jie":"Street",'JIE':"Street","St": "Street", 
           "St.": "Street", "Str":"Street",'Hwy':'Highway', "Ave": "Avenue",
           "lu":"Road","Lu":"Road","Rd.": "Road","road":"Road",
           "hutong":"Alley","Hutong":"Alley","xiang":"Alley","Xiang":"Alley"}

mapping_bank = {"Abc":"中国农业银行","Everbright":"光大银行",'Guangfa Bank':"广发银行", 
           "Agricultural Bank of China": "中国农业银行", "China Merchants Bank":"招商银行",
           "China Minsheng Bank":"民生银行","ICBC":"中国工商银行",
           "Shopping APM Beijing": "中国银行","Beijing Rural Commercial Bank":"北京农商银行",
           "Citic bank":"中信银行","China Mansheng Bank":"民生银行",
           "Hang Seng Bank":"恒生银行","China Bank":"中国银行","China Everbright Bank":'光大银行',
           'Bank Of China':'中国银行','Bank of Jiangsu':'江苏银行','Zhongguo Minsheng Bank':'民生银行',
           'CCB':'中国建设银行','ABC':'中国农业银行','Huaxia Bank':'华夏银行',
           'Bank of China':'中国银行','Bank of Communications':'交通银行',
           'Bank of Beijing':'北京银行',"ICBC Bank":'中国工商银行',
           'Agricultural Bank of China1':'中国农业银行',"China Merchant's Bank":'招商银行',
           'Bank of China Head Office Building':'中国银行总行大厦',
           'China Minsheng Banking Corporation':'民生银行',
           'Industrial and Commercial Bank of China':'中国工商银行',
           'ABC Bank':'中国农业银行','HSBC':'汇丰银行','China Construction Bank':'中国建设银行',
           'Shinhan Bank':'新韩银行','China Postal Savings Bank':'邮储银行',
           'BRCB':'北京农商银行','Citic Bank':'中信银行','SPD Bank':'浦发银行'}


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

# Clean the data
    if is_highway(element):
        for child in element.iter("tag"):
            if is_highway_en_name(child):
                child.attrib['v'] = update_name(child.attrib['v'],mapping)
    if is_bank(element):
        for child in element.iter("tag"):
            if have_name(child):
                child.attrib['v'] = consistent_name(child.attrib['v'],mapping) 

# Shape the data

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    if element.tag == 'node':
        for field in NODE_FIELDS:
            node_attribs[field] = element.attrib[field]

        if len(element):
            for child in element:
                tags_record = {}
                if child.tag == 'tag':
                    problems = PROBLEMCHARS.search(child.attrib['k'])
                    if problems:
                        continue
                    else:
                        colon = LOWER_COLON.search(child.attrib['k'])
                        if colon:
                            tags_record['type'] = child.attrib['k'].split(':',1)[0]
                            tags_record['key'] = child.attrib['k'].split(':',1)[1]
                        else:
                            tags_record['type'] = 'regular'
                            tags_record['key'] = child.attrib['k']
                    tags_record['id'] = element.get('id')
                    tags_record['value'] = child.attrib['v']
                else:
                    continue
                tags.append(tags_record)
        else:
            tags = []
        

        return {'node': node_attribs, 'node_tags': tags}


    elif element.tag == 'way':
        for field in WAY_FIELDS:
            way_attribs[field] = element.attrib[field]

        if len(element):
            for child in (element):
                tags_record = {}
                if child.tag == 'tag':
                    problems = PROBLEMCHARS.search(child.attrib['k'])
                    if problems:
                        continue
                    else:
                        colon = LOWER_COLON.search(child.attrib['k'])
                        if colon:
                            tags_record['type'] = child.attrib['k'].split(':',1)[0]
                            tags_record['key'] = child.attrib['k'].split(':',1)[1]
                        else:
                            tags_record['type'] = 'regular'
                            tags_record['key'] = child.attrib['k']
                    tags_record['id'] = element.attrib['id']
                    tags_record['value'] = child.attrib['v']
                    tags.append(tags_record)
                else:
                    continue
            for index,child in enumerate(element.iter('nd')):
                way_nodes_record = {}
                way_nodes_record['id'] = element.attrib['id']
                way_nodes_record['node_id'] = child.attrib['ref']
                way_nodes_record['position'] = index
                way_nodes.append(way_nodes_record)
                

                
        else:
            tags = []
            way_nodes = []

        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #

# helper functions for cleaning data
def is_highway(elem):
    if elem.tag == 'way':
        for child in elem.iter('tag'):
            if child.attrib['k'] == "highway":
                return elem

def is_highway_en_name(elem):
    return (elem.attrib['k'] == "name:en")

def update_name(name, mapping):
    wrong_name_list = mapping.keys()
    for wrong_name in wrong_name_list:
        if name.endswith(wrong_name):
            name = name.replace(wrong_name,mapping[wrong_name])
    return name

def is_not_chinese(s):
  if s >= u'\u4e00' and s<=u'\u9fa5':
    return False
  else:
    return True

def audit_bank_type(bank_types, bank_name):
    if is_not_chinese(bank_name):
        bank_types[bank_name].add(bank_name)
            
def is_bank(elem):
    if elem.tag == 'node':
        for child in elem.iter('tag'):
            if child.attrib['k'] == "amenity" and child.attrib['v'] == "bank":
                return elem

def have_name(elem):
    return (elem.attrib['k'] == "name")

def consistent_name(name, mapping_bank):
    wrong_name_list = mapping_bank.keys()
    for wrong_name in wrong_name_list:
        if name == wrong_name:
            name = name.replace(wrong_name,mapping[wrong_name])
    return name



def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)

