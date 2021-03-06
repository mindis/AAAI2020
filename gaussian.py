import os
import subprocess
import multiprocessing
from read_dataset import *
import gc
from multiprocessing import Pool, Queue,Manager
import numpy as np
import scipy.sparse
from scipy.sparse import linalg
from functools import partial
from sklearn.datasets import dump_svmlight_file,load_svmlight_file
from sklearn.cluster import KMeans
from sklearn import random_projection
from sklearn import preprocessing
from sklearn.decomposition import PCA
from liblinear.python import liblinearutil
import argparse
from numba import jit
def random(data, tra_label,d_sub, name, what, R,n_label):
    np.set_printoptions(threshold=np.inf, suppress=True)
    label = tra_label
    label = np.mat(label).T
    label = np.where(label[:,0]!=1,-1,1)

    # label = data[:,0]
    # print(data.shape)
    n_sample, f_num= np.shape(data)
    gaussian_transformer = random_projection.GaussianRandomProjection(n_components= d_sub)
    train2 = gaussian_transformer.fit_transform(data)
    gaussian = gaussian_transformer.components_

    label = (np.asarray(label)).reshape(-1)
    dump_svmlight_file(np.around(train2,decimals=4), label, 'other_method/kmeans_linear/%s/%s_gaussian' % (name, what,), zero_based=False)
    #                    zero_based=False)

    sparse_transformer = random_projection.SparseRandomProjection(n_components=d_sub) #transformer attribute component (n_component,n_feature)
    train2 = sparse_transformer.fit_transform(data)
    sparse = sparse_transformer.components_
    # sparse = sparse.todense()
    # exit()
    dump_svmlight_file(np.around(train2,decimals=4), label, 'other_method/kmeans_linear/%s/%s_sparse' % (name, what),
                       zero_based=False)

    test_url = "/home/comp/cszjlei/svm/BudgetedSVM/original/%s/test" % (name)
    # train_url = "/home/comp/cszjlei/svm/BudgetedSVM/original/%s/train" % name
    data, te_label = load_svmlight_file(test_url)

    n_number,d_feature = np.shape(data)
    sub_dimension, transform_len = np.shape(gaussian)
    if transform_len > d_feature:
        ped_matrix = np.zeros((n_number, transform_len - d_feature))
        # print(data.shape,ped_matrix.shape)
        data = scipy.sparse.hstack((data, ped_matrix))
    if transform_len < d_feature:
        data = data[:, :transform_len]
    te_label = np.mat(te_label).T
    np.set_printoptions(threshold=np.inf, suppress=True)
    # data = scipy.sparse.coo_matrix.tocsr(data)
    label = np.where(te_label[:, 0] != 1, -1, 1)
    # print(data.shape,gaussian.shape)
    train2 = scipy.sparse.csr_matrix.dot(data, gaussian.T)
    # print(train2.shape,train2)
    label = (np.asarray(label)).reshape(-1)
    dump_svmlight_file(np.around(train2, decimals=4), label, 'other_method/kmeans_linear/%s/%s_gaussian' % (name, 'test'),
                       zero_based=False)
    #

    train2 = scipy.sparse.csr_matrix.dot(data,sparse.T)
    dump_svmlight_file(np.around(train2, decimals=4), label, 'other_method/kmeans_linear/%s/%s_sparse' % (name, 'test'),
                       zero_based=False)
    # exit()
def read_original(name,n,f_s):
    train_url = "/home/comp/cszjlei/svm/BudgetedSVM/original/%s/train" % (name)
    # train_url = "/home/comp/cszjlei/svm/BudgetedSVM/original/%s/train" % name
    train,tra_label  = load_svmlight_file(train_url)
    n_data, n_feature = np.shape(train)
    sub = int(math.pow(2, f_s) * n_feature)
    if n_feature > 1024:
        power = math.ceil(np.log2(n_feature))
        sub = int(math.pow(2, f_s) * 4096)  #
    R = np.random.choice(int(train.shape[1]) - 1, int(sub), replace=False)
    R = sorted(R)
    # print(train)
    random(data=train,tra_label = tra_label, d_sub=sub,name=name, what='train', R=R, n_label = int(len(tra_label)/2))
def model_training(n,f_idx,i):
    meth = method[i]
    # print(meth)
    y, x = liblinearutil.svm_read_problem("other_method/kmeans_linear/%s/train_%s" % (
        name,meth))
    y_test, x_test = liblinearutil.svm_read_problem("other_method/kmeans_linear/%s/test_%s" % (
        name, meth))

    prob = liblinearutil.problem(y, x)
    temp_result = np.empty((14))

    for idx, val in enumerate(cost):
        param = liblinearutil.parameter(' -q -c %f' % (val))
        m = liblinearutil.train(prob, param)
        pred_labels, (temp_result[idx], MSE, SCC), pred_values = liblinearutil.predict(y_test,x_test,m)
    # print(n,i)
    # print(temp_result)

    return (i, f_idx, n, temp_result)
    # print(i)


def read_acc(rea):
    i, f_idx, n, accuracy = rea
    acc[i, f_idx, n, :] = accuracy[:]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='choose the dataset and training parameter')
    parser.add_argument('-d', action='store', dest='data', help='choose the dataset', default=False)
    parser.add_argument('-m', action='store', dest='landmark', help='choose the landmark point', default=False)
    parser.add_argument('-l', action='store', dest='lambda', help='paremeter for l2 regularzation', default=False)
    parser.add_argument('-g', action='store', dest='gamma', help='gamma for the rbf kernel', default=False)
    param = parser.parse_args()
    method = ['gaussian','sparse']
    np.set_printoptions(threshold=np.inf, suppress=True)
    # method = ['corr','nonuniform']
    tradeoff = [0.2,0.4,0.6,0.8,1]
    f_sub = [-6,-5,-4, -3, -2, -1]
    # f_sub = [-3]
    # f_sub = [-10, -9, -8, -7, -6]
    cost = [2**(-6),2**(-5),2**(-4),2**(-3),2**(-2),2**(-1),1,2,4,8,16,32,64,128]
    name = '%s'%(param.data)
    acc = np.empty((2,len(f_sub),5,14)) #build the matrix to stall the result
    for f_idx,f_s in enumerate(f_sub):

        for n in range(5):
            read_original(name, n, f_s)
            pool = Pool(2)
            f2 = partial(model_training,n,f_idx)
            for j in range(len(method)):
                 pool.apply_async(f2,(j,),callback = read_acc )
            pool.close()
            pool.join()
        # print(acc)
    for idx, val in enumerate(method):
        np.save('other_method/kmeans_linear/%s/%s_result'%(name,val),acc[idx])
        # print(acc[idx])
    for m in method:
        os.remove('other_method/kmeans_linear/%s/train_%s'%(name,m))
        os.remove('other_method/kmeans_linear/%s/test_%s' % (name, m))

