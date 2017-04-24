import subprocess
import os
import sqlite3
import datetime
import sqlQueries
import time
import sklearn
from sklearn import preprocessing, metrics, model_selection, linear_model
import pyglmnet
import numpy
import math
import pickle

# note, for convenience of writing many separate query functions
# the connection is defined globally
dbConn = sqlite3.connect("./LouData.db", detect_types=sqlite3.PARSE_DECLTYPES);
# dbConn.row_factory = sqlite3.Row
dbCursor = dbConn.cursor()
dbCursor.executescript(sqlQueries.E_speedConfigure_0)

def getModelTrainingInput():
    dbCursor.execute(sqlQueries.G_modelTrainingInput_0)
    data = dbCursor.fetchall()
    return numpy.array(data)

def getModelTrainingOutput():
    dbCursor.execute(sqlQueries.G_modelTrainingOutput_0)
    temp = dbCursor.fetchall()

    # flatten the list of tuples received
    flattened = list(sum(temp, ()))
    return numpy.array(flattened)

def getglmnet():
    return pyglmnet.GLM(distr='gaussian', alpha=0.05, score_metric='pseudo_R2')

def getStandardScaler(trainingInput):
    scaler = preprocessing.StandardScaler()
    scaler.fit(trainingInput)
    return scaler

def getTestPredictions(testInput, analysisTool, predictsAnArray):
    if predictsAnArray:
        predictions = []
        for datapoint in testInput:
            predictions.append(numpy.mean(analysisTool.predict(datapoint)))
    else:
        predictions = analysisTool.predict(testInput)

    return predictions

def fitEstimator(tool, paramDict, trainingInput, trainingOutput):

    # track time taken to run search
    start = time.time()
    # newTool = model_selection.GridSearchCV(estimator=tool, param_grid=paramDict, n_jobs=2, pre_dispatch=4, cv=10, refit=True)
    newTool = model_selection.RandomizedSearchCV(estimator=tool, param_distributions=paramDict, refit=True, n_iter=2, verbose=1)
    newTool.fit(trainingInput, trainingOutput)
    end = time.time()
    print '\t HyperParameter Search done in ' + str(end-start) + 'seconds'
    print 'best params...'
    print newTool.best_params_
    return newTool.best_estimator_

def main():

    # get the necessary components to build and use an analysis tool
    print( 'getting input...')
    tInput = getModelTrainingInput()
    print( 'getting output...')
    tOutput = getModelTrainingOutput()
    if len(tInput) != len(tOutput):
        print( 'WARNING training input/output mismatch')

    # get scaler and standardize the input data
    print( 'scaling...')
    scaler = getStandardScaler(tInput)
    tInput = scaler.transform(tInput)
    tInput = tInput[-1000:-1]
    tOutput = tOutput[-1000:-1]

    # get a test input and output set
    print( 'creating data subsets..')
    prelimInput = tInput[0:-500]
    prelimOutput = tOutput[0:-500]
    testInput = tInput[-500: -1]
    testOutput = tOutput[-500: -1]

    # get and pre-train each tool
    print( 'getting tools...')
    print( '\tglm...')
    glmnet = getglmnet()
    glmnet.fit(prelimInput,prelimOutput)

    print '\tard...'
    ardRegressorDict = {'alpha_1': numpy.arange(1.e-6, 1.e-5, 1.e-6), 'alpha_2': numpy.arange(1.e-6, 1.e-5, 1.e-6)}
    ardRegressor = fitEstimator(linear_model.ARDRegression(), ardRegressorDict, prelimInput, prelimOutput)


    # get initial measure of performance
    print( 'R^2 Scores')
    print( 'glmnet - ' + str(metrics.r2_score(y_true=testOutput,y_pred=getTestPredictions(testInput, glmnet, True) )))
    print( 'ardRegressor - ' + str(metrics.r2_score(y_true=testOutput,y_pred=getTestPredictions(testInput, ardRegressor, False))))

    # # refit all tools with the full data
    # print 'refitting...'
    # glmnet.fit(tInput, tOutput)
    # ardRegressor.fit(tInput, tOutput)


    # # save the input scaler and the model for later use
    # print( 'saving scaler and model...')
    # with open("./pickles/scaler.pickle", "wb") as output_file:
    #     pickle.dump(scaler, output_file)
    # with open("./pickles/glmnet.pickle", "wb") as output_file:
    #     pickle.dump(glmnet, output_file)


    dbConn.commit()
    dbConn.close()

if __name__ == "__main__":
    main()
