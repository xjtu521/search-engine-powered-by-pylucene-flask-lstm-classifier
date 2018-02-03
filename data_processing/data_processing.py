from ctypes import cdll, c_char, c_char_p, cast, POINTER
import os.path
import pickle
import os
from sklearn.model_selection import train_test_split
import tensorflow.contrib.learn as learn
import random
from torch.utils.data import Dataset
from collections import defaultdict
from gensim.models import Word2Vec
class dataset(Dataset):
    def __init__(self,texts,labels,vocaber):
        self.texts = texts
        self.labels = labels
        self.vocaber = vocaber

    def __len__(self):
        return len(self.texts)
    def __getitem__(self, index):
        ls = []
        ls.append(self.texts[index])
        return list(self.vocaber.transform(ls)),self.labels[index]


class Text_processing():
    def __init__(self):
        self._lib = None
        self.stopword_set = None
        self.raw_data_file = "/media/zgy/新加卷/formed_data/data_0_300000_?_3023756473.pkl"
        self.keys = ['Title', 'PubDate', 'WBSB', 'DSRXX', 'SSJL', 'AJJBQK', 'CPYZ', 'PJJG', 'WBWB']
        current_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(current_dir,'../../data')
        self.seg_data_file = os.path.join(self.data_dir,'seg_data.pkl')
        self.seg_without_stopword_data = os.path.join(self.data_dir,'seg_without_stopword_data.pkl')
        self.test_data = os.path.join(self.data_dir,'test.txt')
        self.vocaber = os.path.join(self.data_dir,'vocaber.pkl')
        self.max_lenth = 300
        self.min_frequency = 5
    def init_segging(self,model_path=b'', user_dict_path=b'', pre_alloc_size=1024 * 1024 * 16, t2s=False, just_seg=True):

        if self._lib == None:
            path = b"/home/zgy/THULAC.so-master"  # 设置so文件的位置
            self._lib = cdll.LoadLibrary(path + b'/libthulac.so')  # 读取so文件
            if len(model_path) == 0:
                model_path = path + b'/models'  # 获取models文件夹位置
        return self._lib.init(c_char_p(model_path), c_char_p(user_dict_path), pre_alloc_size, int(t2s),
                         int(just_seg))  # 调用接口进行初始化

    def clear(self):
        if self._lib != None: self._lib.deinit()

    def seg(self,sentence):
        sentence = sentence.encode('UTF-8')
        if(self._lib ==None):
            self.init_segging()
        r = self._lib.seg(c_char_p(sentence))
        assert r > 0
        self._lib.getResult.restype = POINTER(c_char)
        p = self._lib.getResult()
        s = cast(p, c_char_p)

        d = '%s' % (s.value.decode("UTF-8"))

        self._lib.freeResult()
        return d

    def init_stop_word(self):
        file = open("../../data/stopword",'r')
        stop_word_set = set()
        for num, i in enumerate(file):
            stop_word_set.add(i[:-1])
        self.stopword_set=stop_word_set
    def remove_stop_word(self,sentence):
        if(self.stopword_set==None):
            self.init_stop_word()
        assert type(sentence) == str
        value_tmp = []

        for i in sentence.split():
            if (i not in self.stopword_set):
                value_tmp.append(i)
        return " ".join(value_tmp)



    def save_seg_data(self,save=True):
        docs = []
        file = open(self.raw_data_file, 'rb')
        jss = pickle.load(file)

        for s, item in enumerate(jss[:-1000]):
            document = item['document']
            document_seg = dict()
            for index, key in enumerate(self.keys):
                if key in document:
                    content = document[key]
                    st_list = []
                    for i in content:
                        if i != '　' and i != ' ':
                            st_list.append(i)
                    content = ''.join(st_list)
                    if (len(content) != 0):
                        content_seg = self.seg(content)
                        document_seg[key] = content_seg
            docs.append(document_seg)
            if (s % 100 == 0):
                print("segging law data",s)
        test_file = open(self.test_data,'w')
        for s, item in enumerate(jss[-1000:]):
            test_file.write('No.'+str(s)+'----------------------'+'\n')
            document = item['document']
            for index, key in enumerate(self.keys):
                if key in document:
                    test_file.write(key+":")
                    test_file.write(document[key])
                    test_file.write('\n')

        file = open(self.seg_data_file,'wb')
        if(save):
            pickle.dump(docs,file)
        return docs

    def load_seg_data(self):
        try:
            file = open(self.seg_data_file,'rb')
        except FileNotFoundError:
            return self.save_seg_data()
        return pickle.load(file)
    def save_seg_without_stopword_data(self,save=True):
        docs = self.load_seg_data()

        for doc in docs:
            for key,value in doc.items():
                value = self.remove_stop_word(value)
                if len(value)>0:
                    doc[key] = value
        file = open(self.seg_without_stopword_data,'wb')
        if(save):
            pickle.dump(docs,file)
        return docs

    def load_seg_without_stopword_data(self, save=True):
        try:
            file = open(self.seg_without_stopword_data,'rb')
        except FileNotFoundError:
            return self.save_seg_without_stopword_data()
        return pickle.load(file)

    def get_labled_cleaned_data(self):
        docs = self.load_seg_without_stopword_data()
        data = []
        target = []
        for doc in docs:
            for index,key in enumerate(self.keys):
                if key in doc:
                    if(len(doc[key])>0):
                        data.append(doc[key])
                        target.append(index)
        return data,target

    def make_label_balance(self,data,target):
        lable_set = set()
        for i in target:
            lable_set.add(i)
        DATA = []
        TARGET = []

        datas = []
        for i in range(9):
            datas.append([])
        for i in zip(data, target):
            d, t = i
            datas[t].append(d)
        mi = min([len(i) for i in datas])
        print(mi)
        for index, i in enumerate(datas):
            i = i[:mi]
            DATA += i
            TARGET += ([index] * mi)

        data, target = DATA, TARGET
        return data,target
    def get_balanced_labled_cleaned_data(self):
        data, target = self.get_labled_cleaned_data()
        return self.make_label_balance(data,target)

    def random_intercept(self,data,target):
        data_tmp = []
        for i in data:
            sentence = i.split()
            if(len(sentence)<10):
                pass
            else:
                l = random.randint(10,min(300,len(sentence)))
                start = random.randint(0,len(sentence)-l)
                stop = start+l
                sentence = sentence[start:stop]


            data_tmp.append(" ".join(sentence))
        data = data_tmp
        return data,target

    def save_vocaber(self):
        data,target = self.get_balanced_labled_cleaned_data()
        vocaber = learn.preprocessing.VocabularyProcessor(self.max_lenth, min_frequency=self.min_frequency)
        vocaber.fit(data)
        file = open(self.vocaber,'wb')
        pickle.dump(vocaber,file)
        return vocaber
    def load_vocaber(self):
        try:
            file = open(self.vocaber, 'rb')
        except FileNotFoundError:
            return self.save_vocaber()
        return pickle.load(file)

    def get_embed(self,sentence):
        vocaber = self.load_vocaber()
        embed = vocaber.transform([sentence])
        return list(embed)[0]
    def cut_head_and_tail(self,data,target):
        s_t = []
        t_t = []
        for sentence,tar in zip(data,target):
            if (tar == 4):

                sentence = sentence.split()
                for num,token in enumerate(sentence):
                    if token=="，" or token=="。":
                        sentence = sentence[num+1:]
                        break
                for i in range(len(sentence)-2,0,-1):
                    if(sentence[i]=="，"or sentence[i]=="。"or sentence[i]=="："):
                        sentence = sentence[:i]
                        break
                sentence = " ".join(sentence)


            elif (tar == 5):
                sentence = sentence.split()
                for num,token in enumerate(sentence):
                    if token=="，" or token=="。":
                        sentence = sentence[num+1:]
                        break
                for i in range(len(sentence)-2,0,-1):
                    if(sentence[i]=="，"or sentence[i]=="。"or sentence[i]=="："):
                        sentence = sentence[:i]
                        break
                sentence = " ".join(sentence)
            elif (tar == 6):
                sentence = sentence.split()
                for num,token in enumerate(sentence):
                    if token=="，" or token=="。":
                        sentence = sentence[num+1:]
                        break
                for i in range(len(sentence)-2,0,-1):
                    if(sentence[i]=="，"or sentence[i]=="。"or sentence[i]=="："):
                        sentence = sentence[:i]
                        break
                sentence = " ".join(sentence)
            s_t.append(sentence)
            t_t.append(tar)
        return s_t,t_t

    def data_cannot_be_recog_by_vocaber(self):
        data, target = self.get_balanced_labled_cleaned_data()
        print("is fitting vocaber")
        vocaber = learn.preprocessing.VocabularyProcessor(self.max_lenth, min_frequency=0)
        vocaber.fit(data)
        new_stop_word = set()
        counter = defaultdict(int)
        print("is counting word")
        for sentence in data:
            for word in sentence.split():
                counter[word]+=1
        for num,d in enumerate(data):
            for word in d.split()[:300]:
                if(counter[word]>=5):
                    if vocaber.vocabulary_.get(word)==0:
                        new_stop_word.add(word)
            if(num%100==0):
                print(num/len(data),end='\r')
        for i in new_stop_word:
            print(i)

    def throw_out_randomly(self,data,target):
        datas = []
        for sentence in data:
            s_s = []
            for word in sentence.split():
                r = random.random()
                if(r>0.1):
                    s_s.append(word)
            datas.append(" ".join(s_s))
        return datas,target

    def re_prep_law_data_for_pytorch(self,train=True):
        data,target = self.get_balanced_labled_cleaned_data()
        data, target = self.cut_head_and_tail(data,target)
        data,target = self.random_intercept(data,target)
        data,target = self.throw_out_randomly(data,target)
        random.seed(1)
        random.shuffle(data)
        random.seed(1)
        random.shuffle(target)

        train_data, test_data = data[:-5000],data[-5000:]
        train_target, test_target = target[:-5000], target[-5000:]
        vocaber = self.load_vocaber()
        if (train):
            return dataset(train_data, train_target, vocaber)
        else:
            return dataset(test_data, test_target, vocaber)



    def whatstop(self):
        model = Word2Vec.load("/media/zgy/新加卷/cuda/zhwiki/model")
        stop_word_new = set()
        data,target=self.get_balanced_labled_cleaned_data()

        for num, i in enumerate(data):
            for word in i.split()[:300]:
                try:
                    model.wv[word]
                except Exception:
                    stop_word_new.add(word)
            if(num%10000==0):
                print(num)
        file = open(os.path.join(self.data_dir,'stopoops'),'w')
        for i in stop_word_new:
            file.write(i)
            file.write('\n')
if __name__=="__main__":
    t=Text_processing()
    s = t.whatstop()