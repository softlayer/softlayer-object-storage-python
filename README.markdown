SoftLayer Object Storage Python Client
======================================
Python bindings for SoftLayer Object Storage

Installation
------------
Download source and run:

```python setup.py install```

To build the documentation (requires sphinx):

```python setup.py build_sphinx```

Basic Usage
----------

```python
import object_storage

sl_storage = object_storage.get_client('YOUR_USERNAME', 'YOUR_API_KEY')

sl_storage.containers()
# []

sl_storage['foo'].create()
# Container(foo)

sl_storage.containers()
# [Container(foo)]

sl_storage['foo']['bar.txt'].create()
# Object(foo, sample_object.txt)

sl_storage['foo']['bar.txt'].send('Plain-Text Content')
# True

sl_storage['foo']['bar.txt'].read()
# 'Plain-Text Content'

sl_storage['foo'].objects()
# [Object(foo, bar.txt)]

sl_storage['foo']['bar.txt'].delete()
# True

sl_storage['foo'].delete()
# True
```

Search Usage
------------
```python
sl_storage.search('bar')
# {'count': 2, 'total': 2, 'results': [Container(foo), Object(foo, foo_object)]}

sl_storage['foo'].search('bar.txt')
# {'count': 1, 'total': 1, 'results': [Object(foo, bar.txt)]}

sl_storage.search('foo', type='container')
# {'count': 1, 'total': 1, 'results': [Container(foo)]}

sl_storage.search('foo*baz')
# {'count': 1, 'total': 1, 'results': [Container(foobarbaz)]}
```

Developement
------------
Follow the [Fork and Pull Request workflow](https://github.com/sevntu-checkstyle/sevntu.checkstyle/wiki/Fork-and-Pull-Request-workflow
). Here's how to get started:

* Fork repo on github
* Clone your new repo to your local machine.

* ``` 
git clone git@github.com:username/softlayer-object-storage-python.git 
```

* Configure remote for upstream.

* ```
cd softlayer-object-storage-python
git remote add upstream git://github.com/softlayer/softlayer-object-storage-python.git
```

* Fetch from upstream

* ``` 
git fetch upstream
```
