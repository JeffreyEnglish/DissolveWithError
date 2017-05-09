#-------------------------------------------------------------------------------
# Name:        DissolveWithError
# Purpose:     And expansion of the Dissolve geoprocessing tool that merges features in classes based on its attributes. This tool allows feature classes with similar but not identical attributes to be merged.
#
# Author:      Jeffrey English
#
# Created:     12-07-2016
# Copyright:   (c) Jeffrey English 2016
#-------------------------------------------------------------------------------

#Import dependencies
import arcpy
from arcpy.da import *
import numpy

#Define a function to dissolve by attributes
def AttributeDissolve(SourceData,Fields,Errors,FIDList):
    #Initialize a numpy array to hold attribute values
    FieldValues = numpy.empty((len(Fields),len(FIDList)))
    #Read attribute values to a numpy array
    for i in range(0,len(Fields)):
        FieldValues[i] = arcpy.da.FeatureClassToNumPyArray(SourceData,Fields[i])

    #Initialize a list of features sorted by attributes
    FieldValuesSorted = [[0]*len(FIDList)]*len(Fields)

    #Sort features by attribute values
    for i in range(0,len(Fields)):
        for j in range(0,len(Fields)-1):
            FieldValuesSorted[i] = FieldValues[i][FieldValues[j].argsort()]

    #Initialize a list of features to keep
    KeepFIDs = list()

    #Loop through features
    for i in range(0,len(FIDList)-1):
        #Reset counter and error variables
        n = 1
        jerror = 0

        #Make a list of values indicating if the item is a duplicate. 1 for unique, 0 for duplicate
        KeepTag = [1]*(len(Fields)-1)

        #Loop through features while difference in attribute values is within error
        while jerror <= Errors[len(Fields)-2] and i+n < len(FIDList)-1:
            #Calculate difference in attribute values for the last compared attribute
            jerror = abs(FieldValuesSorted[len(Fields)-2][i+n] - FieldValuesSorted[len(Fields)-2][i])
            print(i, n)
            print(jerror)
            #If the difference in attribute values is within the error margin do not keep this record based on this attribute
            if jerror <= Errors[len(Fields)-2]:
                KeepTag[len(Fields)-2] = 0
            n = n+1

        #Once the difference is out of range keep the number of potential duplicates
        nmax = n

        #Reset the counter
        n = 1
        #Loop through each compared attributed field
        for j in range(0,len(Fields)-1):
            while n <= nmax:
                #Calculate the difference in attributes
                jerror = abs(FieldValuesSorted[j][i+n] - FieldValuesSorted[j][i])
                #If the difference is within error do not keep this record based on this attribute
                if jerror <= Errors[j]:
                    KeepTag[j] = 0
                n = n+1

        #If there is a unique combination of attributes for this record, keep it
        if sum(KeepTag) > 0:
            KeepFIDs.append(int(FieldValuesSorted[len(Fields)-1][i]))

    #Always keep the last feature
    KeepFIDs.append(int(FieldValuesSorted[len(Fields)-1][len(FIDList)-1]))

    #Return a list of FIDs to keep
    return KeepFIDs

def GeometryDissolve(SourceData,FieldInput,Errors,FIDList):
    #Read the shape geometry
    Geometry = arcpy.da.FeatureClassToNumPyArray(SourceData,FieldInput)
    #create empty list of values
    featurecount = len(FIDList)
    values = [[0]*2]*featurecount
    FieldValues = []
    XCoord = []
    YCoord = []
    KeepFIDs =[]
    FieldValuesSorted = [[0]*52]*featurecount #CHANGE THE 52 TO SMTG MEANINGFUL

    #Remove the prefix of the geometry
    if Geometry[0][0][0:12] == 'MULTIPOLYGON':
        for i in range(0,featurecount):
            record = Geometry[i].tostring()[16:-2]
            #Remove any trailing bytes
            record = record.replace('\x00','')
            #Split the geomtry into individual values
            values[i] = record.split(' ')
            #Remove trailing commas
            for j in range(0,len(values[i])):
                values[i][j] = float(values[i][j].rstrip(','))
            #Convert to a numpy array
            FieldValues.append(numpy.array(values[i]))
            #Split field values in X and Y coordinates
            XCoord.append(FieldValues[i][0::2])
            YCoord.append(FieldValues[i][1::2])
    elif Geometry[0][0][0:5] == 'POINT':
        for i in range(0,featurecount):
            record = Geometry[i][0].tostring()[7:-2]
            #Remove any trailing bytes
            record = record.replace('\x00','')
            #Split the geomtry into individual values
            values[i] = record.split(' ')
            #Convert to a numpy array
            FieldValues.append(numpy.array([float(v) for v in values[i]]))
            #Split field values in X and Y coordinates
            XCoord.append(FieldValues[i][0])
            YCoord.append(FieldValues[i][1])
    elif Geometry[0][0][0:15] == 'MULTILINESTRING':
        for i in range(0,featurecount):
            record = Geometry[i].tostring()[18:-2]
            #Remove any trailing bytes
            record = record.replace('))','')
            record = record.replace('\x00','')
            #Split the geomtry into individual values
            values[i] = record.split(' ')
            #Remove trailing commas
            for j in range(0,len(values[i])):
                values[i][j] = float(values[i][j].rstrip(','))
            #Convert to a numpy array
            FieldValues.append(numpy.array(values[i]))
            #Split field values in X and Y coordinates
            XCoord.append(FieldValues[i][0::2])
            YCoord.append(FieldValues[i][1::2])

    #Compare geometry points
    if Geometry[0][0][0:12] == 'MULTIPOLYGON' or Geometry[0][0][0:15] == 'MULTILINESTRING':
        #Sort by x-coordinate
        for i in range(0,featurecount):
            XCoord[i] = XCoord[i][XCoord[i].argsort()]
            YCoord[i] = YCoord[i][XCoord[i].argsort()]
        for i in range(0,len(XCoord)-1):
            KeepTag = [1]*len(XCoord[i])
            for j in range(0,len(XCoord[i])):
                n = 1
                Xdelta = 0
                while Xdelta < Errors and i+n < featurecount:
                    try:
                        Xdelta = XCoord[i][j] - XCoord[i+n][j]
                        delta = ((XCoord[i][j] - XCoord[i+n][j])**2 + (YCoord[i][j] - YCoord[i+n][j])**2)**0.5
                    except IndexError:
                        n=n+1
                        if i+n == featurecount-1:
                            break
                    else:
                        if delta < Errors:
                            print('KeepTag 0')
                            KeepTag[j] = 0
                        n = n+1
                        if i+n == featurecount-1:
                            break
            if sum(KeepTag) >= 1:
                KeepFIDs.append(FIDList[i])

    elif Geometry[0][0][0:5] == 'POINT':
        #Sort by x-coordinate:
        XCoord = numpy.array(XCoord)[(numpy.array(XCoord)).argsort()]
        YCoord = numpy.array(YCoord)[(numpy.array(XCoord)).argsort()]
        KeepTag = [1]*featurecount
        for i in range(0,len(XCoord)-1):
            n = 1
            while XCoord[i] - XCoord[i+n] < Errors:
                delta = ((XCoord[i] - XCoord[i+n])**2 + (YCoord[i]- YCoord[i+n])**2)**0.5
                if delta < float(Errors):
                    print(delta)
                    KeepTag[i] = 0
                n = n+1
                if i+n == featurecount:
                    break
            if KeepTag[i] >= 1:
                KeepFIDs.append(FIDList[i])

    #Always keep the last features
    KeepFIDs.append(FIDList[len(XCoord)])

    return KeepFIDs

#Read parameters from the arc tool
SourceData = arcpy.GetParameterAsText(0)
FieldInput = (arcpy.GetParameterAsText(1))
ErrorInput = (arcpy.GetParameterAsText(2))
Output = (arcpy.GetParameterAsText(3))
arcpy.env.workspace = (arcpy.GetParameterAsText(4))

#If no field is specified read the shape geometry
if FieldInput == "":
    FieldInput = 'SHAPE@WKT'

#Split the fields into a list
Fields = FieldInput.split(';')
Errors = ErrorInput.split(';')

#Include the identifier in fields
Fields.append('OID@')

#Convert error input values to numpy array of floats
Errors = numpy.asarray([float(i) for i in Errors])

#Provide feedback on the number of features being analyzed
arcpy.MakeFeatureLayer_management(SourceData,'DissolvingData')
arcpy.AddMessage(arcpy.GetCount_management('DissolvingData'))

#Make a list of object IDs
FIDList = list()
rows = arcpy.da.SearchCursor(SourceData,'OID@')
for row in rows:
    FIDList.append(row[0])

#Provide feedback on fields being analyzed
arcpy.AddMessage(len(FIDList))

#Read geometry attributes if dissolving by geometry
if FieldInput == 'SHAPE@WKT':
    GeometryDissolve(SourceData,FieldInput,Errors,FIDList)

#If not dissolving by geometry, dissolve by attributes
else:
    AttributeDissolve(SourceData,Fields,Errors,FieldValues)

#Copy all features to new output file
arcpy.CopyFeatures_management('DissolvingData',Output)

#Remove all features tagged as duplicates
with arcpy.da.UpdateCursor(Output, "OID@") as cursor:
    for row in cursor:
        if row[0] in KeepFIDs:
            pass
        else:
            cursor.deleteRow()

#Set output variable
arcpy.SetParameterAsText(5, Output)