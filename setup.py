from setuptools import setup

setup(name='scwsutil',
      version='0.2',
      url='https://github.com/linhaobuaa/scwsutil/',
      author='linhaobuaa',
      packages=['scwsutil'],
      data_files=[('dict', ['dict/userdic.txt', 'dict/stopword.txt', 'dict/emotionlist.txt', 'dict/one_word_white_list.txt', 'dict/black.txt'])],
      install_requires=[
      ],
      dependency_links=[
          'https://github.com/linhaobuaa/pyscws.git'
      ],
)
