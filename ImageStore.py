'''
Author: Peter Hunt
Website: peterhuntvfx.co.uk
Version: 3.1.2
'''

#You can edit these values, but they lack error checking so be careful
def defaults():

    #These values will override any given to the script, set any 'force' value to True to use the corresponding settings below
    forceCustomFilename = False
    forceCustomImages = False
    forceUpload = False
    forceOpenImageOnUpload = False
    forceDisableSaving = False
    forceCacheWrite = True
    
    customFilename = "ImageStore.png" #May include a path
    customImage = None #Set to None to disable, or give a path
    shouldUpload = True
    shouldOpenImageOnUpload = False
    shouldDisableSaving = False
    shouldWriteCache = True
    
    
    #These just make it easier to set default directories for files
    #If changing the custom directory make sure the folder exists first
    customDirectory = "C:/"
    pythonDirectory = os.getcwd().replace( "\\", "/" )
    userDirectory = os.path.expanduser( "~" ).replace( "\\", "/" )
    
    #Saving the image
    defaultImageName = "ImageDataStore.png"
    defaultImageDirectory = userDirectory
    
    #Saving the cache
    defaultCacheName = "ImageStore.cache"
    defaultCacheDirectory = pythonDirectory
    
    #Displaying a percentage of completion on long calculations
    outputProgressIterations = 2**16 #Check time after this many calculations
    outputProgressTime = 5 #Output progress after this many seconds
    
    output = [[defaultImageName, defaultImageDirectory]]
    output.append( [defaultCacheName, defaultCacheDirectory] )
    output.append( [outputProgressTime, outputProgressIterations] )
    disableList = [[forceCustomFilename, customFilename]]
    disableList.append( [forceCustomImages, customImage] )
    disableList.append( [forceUpload, shouldUpload] )
    disableList.append( [forceOpenImageOnUpload, shouldOpenImageOnUpload] )
    disableList.append( [forceDisableSaving, shouldDisableSaving] )
    disableList.append( [forceCacheWrite, shouldWriteCache] )
    output.append( disableList )
    return output 
    
try:
    from PIL import Image
except:
    raise ImportError( "Python Imaging Library module was not found" )
from random import randint
from subprocess import call
from time import time
from datetime import datetime
import cPickle, base64, urllib2, cStringIO, os, webbrowser, zipfile, getpass, zlib, operator, re, math, md5, itertools

#Disable upload features if requests and pyimgur are not found
printImportError = True #Set this to false if you want to disable the warning if pyimgur or requests are not found
global overrideUpload
try:
    import pyimgur, requests
    overrideUpload = False
except:
    outputText = "Warning: Error importing pyimgur{0}, disabling the upload features."
    try:
        import requests
        outputText = outputText.format( "" )
    except:
        outputText = outputText.format( " and requests" )
    if printImportError == True:
        print outputText
    overrideUpload = True

#Check if running from Maya
global mayaEnvironment
mayaEnvironment = False
try:
    import pymel.core as py
    mayaEnvironment = True
except:
    pass
    
class ImageStore:
    
    defaultValues = defaults()
    defaultImageName = defaultValues[0][0]
    defaultImageDirectory = defaultValues[0][1]
    defaultCacheName = defaultValues[1][0]
    defaultCacheDirectory = defaultValues[1][1]
    outputProgressTime = defaultValues[2][0]
    outputProgressIterations = defaultValues[2][1]
    forceCustomFilenames = defaultValues[3][0][0]
    useThisCustomFilename = defaultValues[3][0][1]
    forceCustomImages = defaultValues[3][1][0]
    useThisCustomImage = defaultValues[3][1][1]
    forceUpload = defaultValues[3][2][0]
    shouldUpload = defaultValues[3][2][1]
    forceOpenOnUpload = defaultValues[3][3][0]
    shouldOpenOnUpload = defaultValues[3][3][1]
    forceDeleteFile = defaultValues[3][4][0]
    shouldDeleteFile = defaultValues[3][4][1]
    forceCacheWrite = defaultValues[3][5][0]
    shouldWriteCache = defaultValues[3][5][1]
    
    #Temporary, will remove later if everything is working properly
    renderViewFormat = "jpg"
    if mayaEnvironment == True:
        renderViewFormatNumber = py.getAttr( "defaultRenderGlobals.imageFormat" )
        if renderViewFormatNumber == 0:
            renderViewFormat = "gif"
        elif renderViewFormatNumber == 1:
            renderViewFormat = "pic"
        elif renderViewFormatNumber == 2:
            renderViewFormat = "rla"
        elif renderViewFormatNumber in [3, 4]:
            renderViewFormat = "tif"
        elif renderViewFormatNumber in [5, 13]:
            renderViewFormat = "sgi"
        elif renderViewFormatNumber == 6:
            renderViewFormat = "als"
        elif renderViewFormatNumber in [7, 10]:
            renderViewFormat = "iff"
        elif renderViewFormatNumber == 8:
            renderViewFormat = "jpg"
        elif renderViewFormatNumber == 9:
            renderViewFormat = "eps"
        elif renderViewFormatNumber == 11:
            renderViewFormat = "cin"
        elif renderViewFormatNumber == 12:
            renderViewFormat = "yuv"
        elif renderViewFormatNumber == 19:
            renderViewFormat = "tga"
        elif renderViewFormatNumber == 20:
            renderViewFormat = "bmp"
        elif renderViewFormatNumber == 23:
            renderViewFormat = "avi"
        elif renderViewFormatNumber in [31, 36]:
            renderViewFormat = "psd"
        elif renderViewFormatNumber == 32:
            renderViewFormat = "png"
        elif renderViewFormatNumber == 35:
            renderViewFormat = "dds"
            
    renderViewSaveLocation = "{0}/RenderViewTemp".format( defaultCacheDirectory )
    imageDataPadding = [116, 64, 84, 123, 93, 73, 106]
    versionNumber = "3.1.1"
    maxCutoffModes = 7
    website = "http://peterhuntvfx.co.uk"
    protocols = ["http://", "https://"]
    debugging = True
    
    def __init__( self, imageName=defaultImageName, **kwargs ):
    
        if self.forceCustomFilenames == True:
            imageName = self.useThisCustomFilename
    
        self.imageName = "{0}.png".format( str( imageName ).replace( "\\", "/" ).rsplit( '.', 1 )[0] )
        
        if "/" not in self.imageName:
            self.imageName = "{0}/{1}".format( self.defaultImageDirectory, self.imageName )
            
        if self.imageName[-1:] == ":":
            self.imageName += "/"
            
        if self.imageName[-1:] == "/":
            self.imageName += self.defaultImageName
        
        
        self.kwargs = kwargs
        self.printProgress = checkInputs.checkBooleanKwargs( kwargs, True, 'p', 'print', 'printProgress', 'printOutput', 'o', 'output', 'outputProgress' )
        
        
    def write( self, input, **kwargs ):
    
        #If image should be uploaded
        upload = checkInputs.checkBooleanKwargs( kwargs, False, 'u', 'upload', 'uploadImage' )
        if overrideUpload == True:
            upload = False
        elif self.forceUpload == True:
            upload = self.shouldUpload
        
        openImage = checkInputs.checkBooleanKwargs( kwargs, True, 'o', 'open', 'openImage', 'openUpload', 'openUploaded', 'openUploadImage', 'openUploadedImage' )
        if self.forceOpenOnUpload == True:
            openImage = self.shouldOpenOnUpload
        
        #If information should be disabled from being displayed
        disableInfo = checkInputs.checkBooleanKwargs( kwargs, False, 'd', 'disable', 'disableInfo', 'disableInformation' )
        
        #If custom image data should be returned but nothing else
        returnCustomImageInfo = checkInputs.checkBooleanKwargs( kwargs, False, 'getInfo', 'returnInfo', 'getCustomInfo', 'returnCustomInfo', 'getImageInfo', 'returnImageInfo', 'getCustomImageInfo', 'returnCustomImageInfo', 'getCustomInformation', 'returnCustomInformation', 'getImageInformation', 'returnImageInformation', 'getCustomImageInformation', 'returnCustomImageInformation' )
        
        #Final validation to read image that has just been created
        validateOutput = checkInputs.checkBooleanKwargs( kwargs, False, 'cO', 'vO', 'checkOutput', 'validateOutput', 'checkImage', 'validateImage' )
        
        #Delete file after creation
        deleteImage = checkInputs.checkBooleanKwargs( kwargs, False, 'dI', 'deleteImage', 'removeImage', 'disableSaving', 'noSave', 'noSaving', 'uploadOnly' )
        if self.forceDeleteFile == True:
            deleteImage = self.shouldDeleteFile
        
        #Output all input data as black to debug
        debugData = checkInputs.checkBooleanKwargs( kwargs, False, 'debug', 'debugData', 'debugResult', 'debugOutput' )
        if debugData == True:
            padWithRandomData = False
        else:
            padWithRandomData = True
            
        #If it should just output the size of input
        outputSize = checkInputs.checkBooleanKwargs( kwargs, False, 's', 'iS', 'oS', 'size', 'inputSize', 'outputSize', 'returnSize', 'sizeOfInput', 'returnInputSize', 'returnSizeOfInput', 'testInput', 'testInputSize' )
        
        #Write image information to cache, can speed up code execution by a lot
        writeToINI = checkInputs.checkBooleanKwargs( kwargs, True, 'DB', 'INI', 'cache', 'writeDB', 'writeINI', 'writeCache', 'writeToDB', 'writeDatabase', 'writeToCache', 'writeToINI', 'writeToDatabase' )
        if self.forceCacheWrite == True:
            writeToINI = self.shouldWriteCache
        
        #If the custom image option should be dynamically disabled or the code stopped
        revertToDefault = checkInputs.checkBooleanKwargs( kwargs, True, 'revert', 'revertToBasic', 'revertToDefault', 'revertToDefaultImage', 'revertToDefaultStyle' )
        
        #If all URLs should be reuploaded to Imgur
        uploadURLsToImgur = checkInputs.checkBooleanKwargs( kwargs, True, 'uploadURLToImgur', 'uploadURLSToImgur', 'uploadCustomURLToImgur', 'uploadCustomURLsToImgur' )
        
        #Write image to render view [Maya only]
        writeToRenderView = checkInputs.checkBooleanKwargs( kwargs, False, 'rV', 'renderView', 'writeToRV', 'writeToRenderView' )
        
        #Cutoff mode help
        cutoffModeHelp = checkInputs.checkBooleanKwargs( kwargs, False, 'cH', 'cMH', 'cHelp', 'cMHelp', 'cutoffHelp', 'cutoffModeHelp' )
        if cutoffModeHelp == True:
            print "Cutoff modes:"
            print "These define if the values should be added or subtracted based on the value of the pixel."
            print "0: Move towards 0"
            print "1: Move towards 64"
            print "2: Move towards 128"
            print "3: Move towards 192"
            print "4: Move towards 255"
            print "5: Move away from 64"
            print "6: Move away from 128"
            print "7: Move away from 192"
            return None
        
        #Ratio of width to height
        validArgs = checkInputs.validKwargs( kwargs, 'r', 'ratio', 'sizeRatio', 'widthRatio', 'heightRatio', 'widthToHeightRatio' )
        ratioWidth = math.log( 1920 ) / math.log( 1920*1080 )
        
        for i in range( len( validArgs ) ):
        
            try:
                if 0 < float( str( kwargs[validArgs[i]] ) ) < 1:
                    ratioWidth = float( str( kwargs[validArgs[i]] ) )
                    break
                    
                else:
                    raise RangeError( "number not in range" )
                    
            except:
                ratioWidth = math.log( 1920 ) / math.log( 1920*1080 )
        
        allOutputs = []
        usedRenderViewImage = False
        if outputSize == False:
        
            #Check if custom image should be used
            validArgs = checkInputs.validKwargs( kwargs, 'i', 'cI', 'img', 'image', 'URL', 'imgURL', 'imgPath', 'imgLoc', 'imgLocation', 'imageURL', 'imageLoc', 'imagePath', 'imageLocation', 'customImg', 'customURL', 'customImage', 'customImgURL', 'customImageURL', 'customImgPath', 'customImagePath', 'customImgLoc', 'customImageLoc', 'customImgLocation', 'customImageLocation' )
            customImageInput = None
            customImageInputPath = ""
            renderViewCheck = checkInputs.capitalLetterCombinations( "Render View" )
            
            #Force certain custom image
            if self.forceCustomImages == True:
                validArgs = ["forceCustomImages"]
                kwargs["forceCustomImages"] = self.useThisCustomImage
                        
            for i in range( len( validArgs ) ):
            
                try:
                    if kwargs[validArgs[i]] == None:
                        validArgs = []
                        break
                    customImageInput = self.readImage( kwargs[validArgs[i]] )
                    if customImageInput != None:
                        customImageInputPath = kwargs[validArgs[i]]
                        break
                    
                    #Read from the Maya Render View window
                    elif mayaEnvironment == True:
                    
                        #Check all combinations of text for render view
                        if kwargs[validArgs[i]] in renderViewCheck:
                            
                            #Save file
                            try:
                                self.renderViewSaveLocation = py.renderWindowEditor( 'renderView', edit = True, writeImage = self.renderViewSaveLocation )[1]
                            except:
                                pass
                            
                            #Get image details
                            customImageInputPath = self.renderViewSaveLocation
                            customImageInput = self.readImage( self.renderViewSaveLocation )
                            
                            if customImageInput != None:
                                usedRenderViewImage = True
                                break
                            else:
                                try:
                                    os.remove( self.renderViewSaveLocation )
                                except:
                                    pass
                        
                except:
                    customImageInput = None
            
            #Check image file path isn't URL, and set to custom image if it is
            usedFilenameAsCustom = False
            if any( value in self.imageName for value in self.protocols ):
            
                outputText = "Error: Can't use URLs when saving an image."
                
                if customImageInput == None and self.forceCustomImages == False:
                    outputText = outputText.replace( ".", ", using URL as a custom image." )
                    customImageInput = self.readImage( self.imageName )
                    
                if self.printProgress == True:
                    print outputText
                    
                self.imageName = self.defaultImageName
                usedFilenameAsCustom = True
                
            
            if ( len( validArgs ) > 0 or usedFilenameAsCustom == True ) and customImageInput == None:
                if self.printProgress == True:
                    print "Error: Custom image could not be read. Output image will be saved without it."
            
            if customImageInput == None:
                useCustomImageMethod = False
            else:
                useCustomImageMethod = True
                
                sizeOfImage = customImageInput.size
                #Keep same size ratio if image can't hold all the data
                ratioWidth = math.log( sizeOfImage[0] ) / math.log( sizeOfImage[0]*sizeOfImage[1] )
            
            
                #Custom cutoff mode
                validArgs = checkInputs.validKwargs( kwargs, 'cM', 'mode', 'cutoff', 'cutoffMode', 'cutoffModes' )
                customCutoffMode = None
                validCustomCutoffModes = []
                for i in range( len( validArgs ) ):
                    try:
                        if "," in str( kwargs[validArgs[i]] ) or type( kwargs[validArgs[i]] ) == tuple:
                        
                            #If provided as tuple
                            if type( kwargs[validArgs[i]] ) == tuple:
                                customModeList = kwargs[validArgs[i]]
                                        
                            #If provided as string
                            else:
                                customModeList = kwargs[validArgs[i]].replace( "(", "" ).replace( ")", "" ).split( "," )
                                       
                            #Build list of all values
                            for j in range( len( customModeList ) ):
                                try:
                                    customCutoffMode = int( customModeList[j] )
                                    if 0 < customCutoffMode < self.maxCutoffModes+1:
                                        validCustomCutoffModes.append( customCutoffMode )
                                except:
                                    customCutoffMode = None
                                    
                            if len( validCustomCutoffModes ) > 0:
                                break
                            
                        else:
                            customCutoffMode = int( kwargs[validArgs[i]] )
                            if 0 < customCutoffMode < self.maxCutoffModes+1:
                                break
                            else:
                                customCutoffMode = None
                                
                    except:
                        customCutoffMode = None
                
                #Run code on final cutoff number
                if len( validCustomCutoffModes ) > 0:
                    customCutoffMode = validCustomCutoffModes[-1]
                
                #If image should be output with all cutoff modes
                allCutoffModes = checkInputs.checkBooleanKwargs( kwargs, False, 'a', 'all', 'aCM', 'allCutoff', 'allCutoffs', 'allModes', 'allCutoffMode', 'allCutoffModes' )
                
                #Automatically set custom cutoff modes to all and disable reverting to the default method if image can't hold data
                if allCutoffModes == True:
                    validCustomCutoffModes = list( range( self.maxCutoffModes+1 ) )
                    revertToDefault = False
                
                
                #Avoid running code again if it's already recursive
                usingCustomModesAlready = checkInputs.checkBooleanKwargs( kwargs, False, 'usingCustomModesAlready' )
                if usingCustomModesAlready == False:
                
                    validCustomCutoffModes.sort()
                    kwargs["usingCustomModesAlready"] = True
                    
                    #Run code again for each cutoff mode
                    for i in range( len( validCustomCutoffModes )-1 ):
                    
                        kwargs["useThisInstead"] = validCustomCutoffModes[i]
                        
                        newImageName = "{0}.m{1}.png".format( self.imageName.replace( ".png", "" ), validCustomCutoffModes[i] )
                        otherURLS = ImageStore( newImageName, **self.kwargs ).write( input, **kwargs )
                        if otherURLS != None:
                            allOutputs += otherURLS
                    
                    if len( validCustomCutoffModes ) > 1:
                    
                        #Set up name and cutoff mode for final run
                        self.imageName = "{0}.m{1}.png".format( self.imageName.replace( ".png", "" ), validCustomCutoffModes[-1] )
                        customCutoffMode = validCustomCutoffModes[-1]
                    
                else:
                    customCutoffMode = kwargs["useThisInstead"]
            
            
            #Test custom image to see if it exists, return True or False
            validArgs = checkInputs.validKwargs( kwargs, 't', 'tI', 'tCI', 'testImage', 'testURL', 'testImageURL', 'testImageLocation', 'testCustomImage', 'testCustomImageURL', 'testCustomImageLocation' )
            canReadCustomImage = False
            for i in range( len( validArgs ) ):
            
                try:
                    if kwargs[validArgs[i]] == True:
                        if customImageInput == None:
                            return False
                        else:
                            return True
                            
                    canReadCustomImage = self.readImage( kwargs[validArgs[i]] )
                    if canReadCustomImage != None:
                        return True
                        
                except:
                    canReadCustomImage = False
                    
            if len( validArgs ) > 0 and canReadCustomImage == False:
                return False
            
            if useCustomImageMethod == True:
                #Find md5 of image
                imageHash = md5.new()
                try:
                    imageHash.update( customImageInput.tostring() )
                except:
                    pass
                imageMD5 = imageHash.hexdigest()
                
                #Open/create text file
                textFileData = {}
                successfulRead = False
                storedImageURL = ""
                
                #This part allows you to skip iterating through every single pixel each time the code is run
                if writeToINI == True:
                    
                    cachePath = self.cache( returnPath = True )
                
                    if os.path.exists( cachePath ):
                        try:
                        
                            textFile = open( cachePath, "r")
                            
                            try:
                            
                                textFileData = self.decodeData( textFile.read(), decode = True )
                                                                    
                                try:
                                
                                    currentImageData = textFileData[imageMD5]
                                    storedCutoffMode = int( currentImageData[0] )
                                    storedValidPixels = currentImageData[1]
                                    storedImageURL = currentImageData[2]
                                    successfulRead = True
                                    
                                except:
                                    pass
                            except:
                                pass
                            textFile.close()
                            
                        except:
                            pass
                            
                        textFile = open( cachePath, "r+")
                    else:
                        textFile = open( cachePath, "w")
                        
                    storedImage = self.readImage( storedImageURL )
                
                
                if successfulRead == True and storedImage != None:
                    
                    customImageInputPath = storedImageURL
                    customImageInput = storedImage
                    
                else:
                    #Upload custom image and switch path to URL
                    uploadCustomImage = checkInputs.checkBooleanKwargs( kwargs, True, 'uI', 'uC', 'uO', 'uCI', 'uploadCustom', 'uploadOriginal', 'uploadCustomImage', 'uploadOriginalImage', 'uploadCustomURL', 'uploadOriginalURL' )
                    if self.forceUpload == True:
                        uploadCustomImage = self.shouldUpload
                    if uploadCustomImage == True and customImageInput != None and overrideUpload != True:
                        
                        #If it should upload any non Imgur URL to Imgur
                        originalImageProtocols = self.protocols
                        if uploadURLsToImgur == True:
                            originalImageProtocols = [str( value ) + "i.imgur" for value in self.protocols]
                        
                        if not any( value in customImageInputPath for value in originalImageProtocols ):
                            
                            if self.printProgress == True:
                                print "Uploading original image..."
                            
                            uploadedImageURL = self.uploadImage( customImageInputPath, ignoreSize = True )
                            
                            if uploadedImageURL != None:
                                if self.printProgress == True:
                                    print "Link to original image is {0}.".format( uploadedImageURL )
                                self.stats( uploadedImageURL, False, imageMD5 )
                                    
                                if writeToINI == False:
                                
                                    if self.printProgress == True:
                                        print "Set this link as the custom image input to avoid re-uploading the same image each time."
                                
                                customImageInputPath = str( uploadedImageURL )
                                customImageInput = self.readImage( uploadedImageURL )
                                                                
                            else:
                                if self.printProgress == True:
                                    print "Original image URL will not be stored within the image."
                                customImageInputPath = ""
                    else:
                        customImageInputPath = ""
        else:
            useCustomImageMethod = False
            
        #Fix for GIF images
        if customImageInputPath[-4:].lower() == ".gif":
            customImageInput = None
            customImageInputPath = ""
            useCustomImageMethod = False
            
            if self.printProgress == True:
                print "Error: Can't use GIF images to write over, disabling the custom image."
            
        
        #Print how large the input data is
        inputData = self.encodeData( input, binary = useCustomImageMethod )
        lengthOfInputData = len( inputData )
        
        if returnCustomImageInfo == False:
            if self.printProgress == True:
                print "Input data is {0} bytes ({1}kb)". format( lengthOfInputData+3, ( lengthOfInputData+3 )/1024 )
        
        #Return the normal size of input data
        if outputSize == True:
            return lengthOfInputData+3, (lengthOfInputData+3)*8
        
        rawData = []
        if useCustomImageMethod == True:
            
            if returnCustomImageInfo == False:
                if self.printProgress == True:
                    print "Checking image has enough pixels to store the input data. This may take a while."
            
            bitsPerPixel = 6
            
            #Get correct range
            cutoffModeAmount = {}
            colourRange = {}
            cutoffModes = range( self.maxCutoffModes+1 )
            invalidCutoffMode = len( cutoffModes )
            
            #Set up valid pixels dictionary
            validPixels = {}
            for i in cutoffModes:
                cutoffModeAmount[i] = 0
                colourRange[i] = self.validRange( i, bitsPerPixel )
                validPixels[i] = {}
            
            #Read valid pixels dictionary from cache
            if successfulRead == True and ( 0 <= storedCutoffMode <= self.maxCutoffModes ):
                validPixels = storedValidPixels
                bestCutoffMode = storedCutoffMode
            else:
                bestCutoffMode = None
                storedCutoffMode = invalidCutoffMode
                
            #Use custom cutoff mode
            if customCutoffMode != None:
                storedCutoffMode = customCutoffMode
                
            if successfulRead == False or len( validPixels[storedCutoffMode] ) == 0 or bestCutoffMode == None:

                #Calculate max data that can be stored
                if self.printProgress == True:
                    if storedCutoffMode == invalidCutoffMode:
                        print "Calculating the best method to store data..."
                        
                totalPixelCount = 0
                imageDimensions = customImageInput.size
                imageSize = float( imageDimensions[0]*imageDimensions[1] )
                pixelCount = 0
                
                nextTime = time()+self.outputProgressTime
                for pixels in customImageInput.getdata():
                    
                    #Output progress
                    if pixelCount % self.outputProgressIterations == 0:
                        if nextTime < time():
                            nextTime = time()+self.outputProgressTime
                            if self.printProgress == True:
                                print " {0}% completed".format( round( 100 * totalPixelCount / imageSize, 1 ) )
                
                        for rgb in range( 3 ):
                            rawData.append( pixels[rgb] )
                            if bestCutoffMode == None:
                                #Count all valid values to find best cutoff mode
                                if totalPixelCount > 0:
                                    for i in cutoffModes:
                                        if pixels[rgb] in colourRange[i][0] or pixels[rgb] in colourRange[i][1]:
                                            cutoffModeAmount[i] += 1
                                    
                    totalPixelCount += 1
                  
                #Select best cutoff mode
                if bestCutoffMode == None:
                    bestCutoffMode = max( cutoffModeAmount.iteritems(), key=operator.itemgetter( 1 ) )[0]
                    cutoffMode = bestCutoffMode
                else:
                    cutoffMode = storedCutoffMode
                      
                
                if self.printProgress == True:
                    print "Using storing mode {0}.".format( cutoffMode )
                    print "Calculating how much data can be stored for different amounts of bits using this mode..."
                
                #Find maximum size image can store for bits per colour
                nextTime = time()+self.outputProgressTime
                
                pixelCount = 0
                totalCount = float( 8*len( rawData ) )
                bitsPerPixel = 0
                for i in range( 8 ):
                                            
                    bitsPerPixel = i+1
                    validPixels[cutoffMode][bitsPerPixel] = 0
                    colourIncreaseRange, colourReduceRange = self.validRange( cutoffMode, bitsPerPixel )
                    
                    for j in range( len( rawData ) ):
                    
                        if rawData[j] in colourIncreaseRange or rawData[j] in colourReduceRange:
                            validPixels[cutoffMode][bitsPerPixel] += 1
                            
                        #Output progress
                        pixelCount += 1
                        if pixelCount % self.outputProgressIterations == 0:
                            if nextTime < time():
                                nextTime = time()+self.outputProgressTime
                                if self.printProgress == True:
                                    print " {0}% completed".format( round( 100 * pixelCount / totalCount, 1 ) )
                        
            else:
            
                if self.printProgress == True:
                    print "File information read from cache."
                    
                #Store custom image information
                for pixels in customImageInput.getdata():
                    for rgb in range( 3 ):
                        rawData.append( pixels[rgb] )
                        
                #Get stored values
                cutoffMode = storedCutoffMode
                if customCutoffMode != None:
                    cutoffMode = customCutoffMode
                validPixels = storedValidPixels
                
                if self.printProgress == True:
                    print "Using storing mode {0}.".format( cutoffMode )
            
            validPixelsTotal = [number*bits for number, bits in validPixels[cutoffMode].iteritems()]
            bitsPerPixelMax = validPixelsTotal.index( max( validPixelsTotal ) )+1
            
            #Write to ini file
            if writeToINI == True:
                textFileData[imageMD5] = [bestCutoffMode, validPixels, customImageInputPath]
                textFile.write( self.encodeData( textFileData, encode = True ) )
                textFile.close()
            
            #Get maximum bytes per bits
            imageBytes = validPixels[cutoffMode][ bitsPerPixelMax ]
            if self.printProgress == True:
                print "Image can store up to around {0} bytes ({1}kb)".format( imageBytes, imageBytes/1024 )
            
            inputBytes = ( len(inputData )*8 )/bitsPerPixelMax+3
            outputText = "Input data at this level is {0} bytes ({1}kb)".format( inputBytes, inputBytes/1024 )
            
            if inputBytes > imageBytes:
                outputText += ", which is currently more than the image can hold."
                outputText += "\nAttempting to find a valid value by calculating the other levels."
                
            else:
                outputText += ", now attempting to find the minumum valid value to store the data."
                
            if self.printProgress == True:
                print outputText
            
            #Stop here if image information is wanted
            if returnCustomImageInfo == True:
                return imageBytes
            
            #Calculate minimum bits per pixel to use
            #Higher does not necessarily mean more, 6 bits seems to be the most efficient one
            bitsPerPixel = 1
            bytesNeeded = ( lengthOfInputData*8 )/bitsPerPixel+3 #Avoids having to actually split the input data
            
                
            while validPixels[cutoffMode][bitsPerPixel] < bytesNeeded:
            
                if bitsPerPixel > 7:
                    
                    outputText = "Error: Image not big enough to store data."
                        
                    #Stop code here if reverting to default isn't an option
                    if revertToDefault == False:
                        if self.printProgress == True:
                            print outputText
                        return None
                    else:
                        outputText += " Disabling the custom image option."
                        if self.printProgress == True:
                            print outputText
                    
                    useCustomImageMethod = False
                    inputData = self.encodeData( input, binary = useCustomImageMethod )
                    
                    break
                    
                bitsPerPixel += 1
                bytesNeeded = ( lengthOfInputData*8 )/bitsPerPixel+3
            
            
            #Continue if valid, if not pass through
            if bitsPerPixel < 8:
                if self.printProgress == True:
                    if bitsPerPixel > 1:
                        print "Increased to {0} bits of colour to fit data within the image.".format( bitsPerPixel )
                    else:
                        print "Using 1 bit of colour to fit data within the image."
    
                #Encode input data
                joinedData = "".join( inputData )
                splitData = re.findall( r".{1," + str( bitsPerPixel ) + "}", joinedData, re.DOTALL )
                colourIncreaseRange, colourReduceRange = self.validRange( cutoffMode, bitsPerPixel )
                numbersToAdd = [ int( num, 2 ) for num in splitData ]
                
                #Draw image
                width, height = customImageInput.size
        
        if useCustomImageMethod == False:
            
            #Set image info
            minimumWidth = 3
            height = 2
            currentPixels = len( inputData )/3
            
            #Calculate width and height
            if currentPixels <= minimumWidth*height:
                #Set to minimum values
                width = minimumWidth
                
            else:
                #Calculate based on ratio
                width = int( round( pow( currentPixels, ratioWidth ), -1 ) )
                #Make sure it is divisible by 3
                width /= 3
                width *= 3
                if width < minimumWidth:
                    width = minimumWidth
                    
                #Correct size to allow for padding
                while currentPixels > height*width:
                    if width <= height and ratioWidth > 0.5:
                        width += 1
                    else:
                        height += 1
            bitsPerPixel = 8
            cutoffMode = 9
    
            if self.printProgress == True:
                print "Set width to {0} pixels and height to {1} pixels.".format( width, height )
        
        #Draw image
        imageOutput = Image.new("RGB", ( width, height ) )
        imageData = imageOutput.load()
    
        #Set range of colours for random filling
        numbersToAddIncrement = 0
        if padWithRandomData == True:
        
            if useCustomImageMethod == True:
                maxImageAddition = pow( 2, bitsPerPixel )+bitsPerPixel-8
                minImageAddition = 0
                
                #Fix for if it goes under 1
                if maxImageAddition < 1:
                    maxImageAddition = pow( 2, bitsPerPixel )
                
            else:
                maxImageAddition = 128
                minImageAddition = 52
                
        else:
            maxImageAddition = 255
            minImageAddition = 255
        
        #Assign pixel colours
        for y in range( height ):
            for x in range( width ):
                
                isDataFromInput = True
                currentProgress = 3*( y*width+x )
                
                #Assign information to first pixel
                if x == 0 and y == 0:
                    inputInfo = int( str( bitsPerPixel ) + str( cutoffMode ) )
                    dataRGB = [inputInfo, inputInfo, inputInfo]
                    if debugData == True:
                        dataRGB = [99,99,99]
                        imageData[x,y] = tuple( dataRGB )
                        continue
                
                #If an image should be made with the default method
                elif useCustomImageMethod == False:
                        
                    dataRGB = {} 
                    try:
                        for i in range( 3 ):
                            dataRGB[i] = inputData[numbersToAddIncrement]
                            numbersToAddIncrement += 1
                    except:
                    
                        if isDataFromInput == True:
                            isDataFromInput = False
                        
                        #Add random data
                        for i in range( 3 ):
                            dataRGB[i] = randint( minImageAddition, maxImageAddition )
                    
                    dataRGB = [ number[1] for number in dataRGB.items()]
                     
                #If data should be written over a custom image
                else:
                
                    if numbersToAddIncrement < len( numbersToAdd )-1:
                        dataRGB = {}
                        for i in range( 3 ):
                        
                            try:
                                if rawData[currentProgress+i] in colourIncreaseRange:
                                    dataRGB[i] = rawData[currentProgress+i] + numbersToAdd[numbersToAddIncrement]
                                    numbersToAddIncrement += 1
                                    
                                elif rawData[currentProgress+i] in colourReduceRange:
                                    dataRGB[i] = rawData[currentProgress+i] - numbersToAdd[numbersToAddIncrement]
                                    numbersToAddIncrement += 1
                                    
                                else:
                                    dataRGB[i] = rawData[currentProgress+i]
                                    
                            except:
                                dataRGB[i] = rawData[currentProgress+i]
                                isDataFromInput = False
                                
                        dataRGB = [ dataRGB[0], dataRGB[1], dataRGB[2] ]
                        
                    else:
                    
                        if isDataFromInput == True:
                            isDataFromInput = False
                        
                        #Pad with random values so it's not such a clear line in the image
                        dataRGB = {}
                        for i in range( 3 ):
                        
                            if rawData[currentProgress+i] in colourIncreaseRange:
                                dataRGB[i] = rawData[currentProgress+i] + randint( minImageAddition, maxImageAddition )
                                
                            elif rawData[currentProgress+i] in colourReduceRange:
                                dataRGB[i] = rawData[currentProgress+i] - randint( minImageAddition, maxImageAddition )
                                
                            else:
                                dataRGB[i] = rawData[currentProgress+i]
                                
                        dataRGB = [ dataRGB[0], dataRGB[1], dataRGB[2] ]
                
                if debugData == True and isDataFromInput == True:
                    dataRGB = [0,0,0]
                    
                imageData[x,y] = tuple( dataRGB )
        
        try:
            imageOutput.save( self.imageName, "PNG" )
            
        except:
        
            failText = ["Error: Failed saving file to {0}.".format( self.imageName )]
            failText.append( "You may have incorrect permissions or the file may be in use." )
            failText.append( "\nAttempting to save in new location..." )
            if self.printProgress == True:
                print " ".join( failText )
            savingFailed = "\nFailed to save file."
            
            #If already in default directory
            if self.imageName.rsplit( '/', 1 )[0] == self.defaultImageDirectory:
            
                if self.imageName.rsplit( '/', 1 )[1] == self.defaultImageName:
                    self.imageName = None
                    failText = savingFailed
                    
                else:
                
                    try:
                        self.imageName = "{0}/{1}".format( self.defaultImageDirectory, self.defaultImageName )
                        imageOutput.save( self.imageName, "PNG" )
                        failText = None
                        
                    except:
                        self.imageName = None
                        failText = savingFailed
                        
            #If not in default directory
            else:
            
                try:
                    self.imageName = "{0}/{1}".format( self.defaultImageDirectory, self.imageName.rsplit( '/', 1 )[1] )
                    imageOutput.save( self.imageName, "PNG" )
                    failText = None
                    
                except:
                
                    try:
                        self.imageName = "{0}/{1}".format( self.defaultImageDirectory, self.defaultImageName )
                        imageOutput.save( self.imageName, "PNG" )
                        failText = None
                        
                    except:
                        failText = savingFailed
                        self.imageName = None
        
        
        #Make sure image exists first
        if self.imageName != None:
            
            #Write to render view window for Maya
            if mayaEnvironment == True:
                if writeToRenderView == True:
                    try:
                        py.renderWindowEditor( 'renderView', edit = True, loadImage = self.imageName, caption = "Image Store File" )
                    except:
                        print "Error: Failed to load image into renderView"
                
                try:
                    os.remove( self.renderViewSaveLocation )
                except:
                    pass
            
            #Find md5 of image
            imageHash = md5.new()
            try:
                imageHash.update( self.readImage( self.imageName ).tostring() )
            except:
                pass
            imageMD5 = imageHash.hexdigest()
            
            if self.printProgress == True:
                print "Saved image."
            
            outputList = [( self.imageName ).replace( "\\", "/" )]
            
            #Zip extra information inside image
            if self.printProgress == True:
                print "Writing extra information into image file."
                
            infoText = ["Date created: {0}\r\n".format( self.dateFormat( time() ) )]
            try:
                infoText = ["Username: {0}".format( getpass.getuser() ) + "\r\n"] + infoText
            except:
                pass
            infoText.append( "Visit {0} to get a working version of the code.".format( self.website ) )
            
            #Write to zip file
            if disableInfo == False:
                ImageStoreZip.write( "".join( infoText ), "information.txt", reset = True )
                ImageStoreZip.write( str( getpass.getuser() ) + "@" + str( time() ), "creationtime" )
                ImageStoreZip.write( customImageInputPath, "url" )
            else:
                ImageStoreZip.write( infoText[-1], "information.txt", reset = True )
            ImageStoreZip.write( str( self.versionNumber ), "version" )
            
            zipSuccess = ImageStoreZip.combine( image = self.imageName )
            
            if zipSuccess == False:
                if self.printProgress == True:
                    print "Error: Unable to write extra information."
            
            #Upload image
            uploadedImageURL = None
            if upload == True and overrideUpload != True:
                if self.printProgress == True:
                    print "Uploading image..."
                    
                uploadedImageURL = self.uploadImage( self.imageName, openImage )
                if uploadedImageURL != None:
                    outputList.append( str( uploadedImageURL ) )
                    
            if self.printProgress == True:
                print "Done."
            
            if deleteImage == True:
                try:
                    os.remove( self.imageName )
                    outputList.pop( 0 )
                except:
                    pass
                if len( outputList ) == 0:
                    return None
            
            #Check the output
            if validateOutput == True:
                try:
                    if self.read() != input:
                    
                        raise ImageStoreError( "data failed to validate" )
                        
                    else:
                        if self.printProgress == True:
                            print "Successfully validated the data."
                        
                except:
                    if self.printProgress == True:
                        print "Error: Failed to validate the data. Please try again."
                    return None
            
            
            self.stats( uploadedImageURL, lengthOfInputData+3, imageMD5 )
            
            #Return output
            allOutputs += [outputList]
            return allOutputs
            
        else:
            return None

    #This is my only way of finding the stats as imgur doesn't say, this won't be available to view anywhere
    #However, if you are against this, just disable the urllib2.urlopen() command
    def stats( self, imageURL, numBytes, imageMD5 ):
    
        #Check if md5 value is valid
        if md5.new().hexdigest() == imageMD5:
            imageMD5 = "".join("0" for x in range( 32 ))
            return #No point storing it currently, means something has gone wrong or something
            
        #Set user agent and URL
        userAgent = "ImageStore/" + str( self.versionNumber )
        siteAddress = "{0}/code/imagestore?url={1}&b={2}&m={3}".format( self.website, imageURL, int( numBytes ), imageMD5 )
        
        #Send a request to the website
        try:
            if self.debugging != True:
                urllib2.urlopen( urllib2.Request( siteAddress, headers = { 'User-Agent': userAgent } ) )
        except:
            pass
        
        
    def uploadImage( self, imageLocation, openImage = False, **kwargs ):
        
        ignoreSize = checkInputs.checkBooleanKwargs( kwargs, False, 'i', 'iS', 'ignoreSize' )
        imageTitle = "Image Data"
        
        if self.validPath( imageLocation ) == True and overrideUpload != True:
        
            #Save if from a URL
            saved = False
            if any( value in imageLocation for value in self.protocols ):
            
                try:
                    inputImage = Image.open( cStringIO.StringIO( urllib2.urlopen( imageLocation ).read() ) )
                    imageFormat = str( inputImage.format )
                    imageSaveLocation = "{0}/{1}.{2}".format( self.defaultCacheDirectory, self.defaultCacheName, imageFormat.lower() ).replace( ".cache", "" )
                    inputImage.save( imageSaveLocation, imageFormat ) 
                    imageLocation = imageSaveLocation
                    saved = True
                    
                except:
                    pass
                
            #Upload image
            try:
                uploadedImage = pyimgur.Imgur( "0d10882abf66dec" ).upload_image( imageLocation, title=imageTitle )
            
            except:
                if self.printProgress == True:
                    print "Error: Failed uploading image, trying once more."
                    
                #Once it didn't upload the first time, no idea why, but I guess this just makes sure your internet didn't temporarily cut out
                try:
                    uploadedImage = pyimgur.Imgur( "0d10882abf66dec" ).upload_image( imageLocation, title=imageTitle )
                
                except:
                    if self.printProgress == True:
                        print "Failed to upload image."
                    return None
            
            #Find out image size
            originalImageSize = os.path.getsize( imageLocation )
            uploadedImageSize = uploadedImage.size
            
            #Check it's not been converted, not needed if it's acting as the original image
            if originalImageSize != uploadedImageSize and ignoreSize == False:
            
                if self.printProgress == True:
                    print "Error: File is too large for imgur."
                return None
                
            else:
            
                #Open image in browser
                if openImage == True:
                    webbrowser.open( uploadedImage.link )
                                
                #Return the link
                return uploadedImage.link

            if saved == True:
            
                try:
                    os.remove( imageSaveLocation )
                    
                except:
                    pass
        
        else:
            return None
                
    def read( self, *args, **kwargs ):
    
        useCustomImageMethod = False
        debugDataDefaultAmount = 100 #How many characters to display by default
        
        #If it should just debug the data
        validArgs = checkInputs.validKwargs( kwargs, 'debug', 'debugData', 'debugResult', 'debugOutput' )
        debugData = False
        for i in range( len( validArgs ) ):
            try:
                if kwargs[validArgs[i]] == True:
                    debugData = debugDataDefaultAmount
                    break
                elif 0 < int( kwargs[validArgs[i]] ):
                    debugData = int( kwargs[validArgs[i]] )
            except:
                debugData = False
        if debugData == False and self.debugging == True:
            debugData = debugDataDefaultAmount

        #Get image
        imageInput = self.readImage( self.imageName )
        if imageInput == None:
            if self.printProgress == True:
                print "Error: Unable to read image."
            return None
            
        #Output stored zip information
        outputInfo = checkInputs.checkBooleanKwargs( kwargs, debugData, 'o', 'output', 'outputInfo', 'outputInformation' )
        
        try:
            originalVersionNumber, originalCreationTime, originalCreationName, customImageURL, fileList = ImageStoreZip.read( imageLocation = self.imageName )
            if debugData != False and self.printProgress == True:
                print "Files stored in image: {0}".format( ", ".join( fileList ) )
        
        except:
            outputInfo = False
            customImageURL = ""
            
        if outputInfo == True:
            if originalVersionNumber != None:
                print "Version number: {0}".format( originalVersionNumber )
            if originalCreationTime != None:
                print "Date created: {0}".format( self.dateFormat( originalCreationTime ) )
        
        #Store pixel info
        rawData = []
        for pixels in imageInput.getdata():
            for rgb in range( 3 ):
                rawData.append( pixels[rgb] )
                
        #Get important image info
        imageInfo = [int( num ) for num in list( str( rawData[0] ) )]
        bitsPerPixel = imageInfo[0]
        cutoffMode = imageInfo[1]
        
        if debugData != False and self.printProgress == True:
            print "Bits per pixel: {0}\r\nCutoff mode: {1}".format( bitsPerPixel, cutoffMode )
        
        #Find how the image was made
        if bitsPerPixel == 9 and cutoffMode == 9:
            if self.printProgress == True:
                print "Error: Image had debug data set to true. Unable to read."
            return None
            
        elif len( imageInfo ) > 2:
            if self.printProgress == True:
                outputText = "Stored data {0}."
                if str( originalVersionNumber ) != str( self.versionNumber ):
                    outputText.format( "is from an older version {0}" )
                else:
                    outputText.format( "appears to be invalid {0} anyway" )
                outputText.format( ", attempting to continue" )
                useCustomImageMethod = False
                
        elif bitsPerPixel == 8:
            useCustomImageMethod = False
        else:
            useCustomImageMethod = True
            
        usedDifferentOriginalImage = False
        if useCustomImageMethod == True:
        
            #Store pixel info
            imageInput = self.readImage( self.imageName )
            rawData = []
            for pixels in imageInput.getdata():
                for rgb in range( 3 ):
                    rawData.append( pixels[rgb] )
             
            #Use other custom image
            validArgs = checkInputs.validKwargs( kwargs, 'i', 'cI', 'img', 'image', 'URL', 'imgURL', 'imgPath', 'imgLoc', 'imgLocation', 'imageURL', 'imageLoc', 'imagePath', 'imageLocation', 'customImg', 'customImage', 'customImgURL', 'customImageURL', 'customImgPath', 'customImagePath', 'customImgLoc', 'customImageLoc', 'customImgLocation', 'customImageLocation' )
            originalImage = None
            for i in range( len( validArgs ) ):
                try:
                    originalImage = self.readImage( kwargs[validArgs[i]] )
                except:
                    originalImage = None
            
            #Try read from args instead
            if originalImage == None:
                try:
                    originalImage = self.readImage( args[0] )
                except:
                    originalImage = None
            
            if len( validArgs ) > 0 and originalImage == None:
            
                if self.printProgress == True:
                    outputText = "Error: Could not read the custom input image."
                    if len( customImageURL ) > 0:
                        outputText.replace( ".", ", reverting to the stored URL." )
                    print outputText
                    
                originalImage = self.readImage( customImageURL )
                
            elif originalImage == None:
                originalImage = self.readImage( customImageURL )
                
            else:
                usedDifferentOriginalImage = True
                
            #If both attempts haven't worked
            if originalImage == None:
                if len( customImageURL ) > 0:
                    if self.printProgress == True:
                        print "Error: Invalid custom image."
                return None
                
            #Store original pixel info
            originalImageData = []
            for pixels in originalImage.getdata():
                for rgb in range( 3 ):
                    originalImageData.append( pixels[rgb] )
                    
            #For cutoff mode, 0 is move colours down towards black, 1 is move towards middle, 2 is move towards white
            bitsPerColour, cutoffMode = [int( x ) for x in list( str( rawData[0] ) )]
            colourIncreaseRange, colourReduceRange = self.validRange( cutoffMode, bitsPerColour )
            
            #Get difference in data
            comparisonData = []
            for i in range( 3, len( originalImageData ) ):
            
                if originalImageData[i] in colourIncreaseRange:
                    comparisonData.append( rawData[i] - originalImageData[i] )
                    
                elif originalImageData[i] in colourReduceRange:
                    comparisonData.append( originalImageData[i] - rawData[i] )
                    
            bitData = "".join( [ format( x, "b" ).zfill( bitsPerColour ) for x in comparisonData ] )
            byteData = re.findall( r".{1,8}", bitData )
            
            for i in range( len( byteData ) ):
                if "-" in byteData[i]:
                    byteData[i] = "00000000"
                    
            numberData = [ int( number, 2 ) for number in byteData ]
            
        else:
            numberData = rawData[3:]
    
        #Truncate end of file
        try:
        
            for i in range( len( numberData ) ):
                j = 0
                
                while numberData[i+j] == self.imageDataPadding[j]:
                    j += 1
                    
                    if j == len( self.imageDataPadding ):
                        numberData = numberData[0:i]
                        break
                        
                if j == len( self.imageDataPadding ):
                    break
                    
        except:
            if self.printProgress == True:
                print "Error: File is corrupted."
                
        try:
            decodedData = self.decodeData( numberData )
            
        except:
            if self.printProgress == True:
            
                if usedDifferentOriginalImage == True:
                    print "Failed to decode data, the custom original image specified may not be the original one used."
                    
                    if len( customImageURL ) > 0:
                        print "Failed to decode data, however here is a URL to the correct image contained within the file."
                        print "If you are using the original image stored on your computer, it may have resized after being uploaded to Imgur."
                    
                    else:
                        print "No URL was found stored in the image, you may have linked to the wrong image."
                
                elif len( customImageURL ) > 0:
                    print "Failed to decode data from the stored URL ({0}), check the image still exists.".format( customImageURL )
                
                else:
                    print "Failed to decode data from the image."
                    
            decodedData = None
        
        if debugData != False and self.printProgress == True:
            print "Length of stored data: {0}\r\nType of data: {1}".format( len( decodedData ), str( type( decodedData ) ).replace( "<type '", "" ).replace( "'>", "" ) )
            if len( str( decodedData ) ) > debugData:
                print "First {0} characters of data: {1}".format( debugData, str( decodedData )[0:debugData] )
            else:
                print "Stored data: {0}".format( decodedData )
        
        return decodedData

    def decodeData( self, numberData, **kwargs ):
        
        #Only decode the data without converting numbers into characters
        if checkInputs.checkBooleanKwargs( kwargs, False, 'd', 'decode', 'decodeOnly' ) == True:
            encodedData = numberData
        
        #Convert numbers into characters
        else:
            encodedData = "".join( [chr( pixel ) for pixel in numberData] )
        outputData = cPickle.loads( zlib.decompress( base64.b64decode( encodedData ) ) )
        
        return outputData
    
    def encodeData( self, input, **kwargs ):
        
        encodedData = base64.b64encode( zlib.compress( cPickle.dumps( input ) ) )
        if checkInputs.checkBooleanKwargs( kwargs, False, 'e', 'encode', 'encodeOnly' ) == True:
            return encodedData
        
        #Format into numbers
        pixelData = [int( format( ord( letter ) ) ) for letter in encodedData]
        pixelData += self.imageDataPadding
        
        #Pad to end with multiple of 3
        for i in range( 3-len( pixelData )%3 ):
            pixelData += [randint( 52, 128 )]
        
        #Get binary info
        binary = checkInputs.checkBooleanKwargs( kwargs, False, 'b', 'binary', 'useCustomImageMethod' )
        if binary == True:
            pixelData = [ format( number, "b" ).zfill( 8 ) for number in pixelData ]
            
        return pixelData      
    
    #Format the time float into a date
    def dateFormat( self, input ):
        return datetime.fromtimestamp( float( input ) ).strftime( '%d/%m/%Y %H:%M' )

    #Find if path/file exists
    def validPath( self, path, **kwargs ):
       
        #This will truncate the final slash, to make sure the directory exists
        includeFile = checkInputs.checkBooleanKwargs( kwargs, False, 'f', 'iF', 'iI', 'file', 'image', 'include', 'isFile', 'isImage', 'includeFile', 'includeImage', 'includesFile', 'includesImage' )
       
        path = str( path )
        
        #Check URL and local paths separately
        if any( value in path for value in self.protocols ):
            try:
                Image.open( cStringIO.StringIO( urllib2.urlopen( path ).read() ) )
                isValid = True
            except:
                isValid = False
                
        else:
            if includeFile == True and "." in path.rsplit( '/', 1 )[1]:
                path = path.rsplit( '/', 1 )[0]
                
            isValid = os.path.exists( path )
        
        
        return isValid

    #Work out pixel values to affect
    def validRange( self, cutoffMode, bitsPerColour ):
        
        cutoffRange = pow( 2, bitsPerColour )
        
        if cutoffMode < 5:
            colourMinIncrease = 0
            colourMaxIncrease = cutoffMode*64-cutoffRange-1
            colourMaxReduce = 255
            colourMinReduce = cutoffMode*64+cutoffRange
        elif cutoffMode < 8:
            cutoffMode -= 4
            colourMinIncrease = cutoffMode*64
            colourMaxIncrease = 255-cutoffRange
            colourMinReduce = cutoffRange
            colourMaxReduce = cutoffMode*64-1
        else:
            colourMinIncrease = 0
            colourMaxIncrease = -1
            colourMinReduce = 255
            colourMaxReduce = 254
        
        colourIncreaseRange = range( colourMinIncrease, colourMaxIncrease+1 )
        colourReduceRange = range( colourMinReduce, colourMaxReduce+1 )
        
        return colourIncreaseRange, colourReduceRange
        
    def cache( self, **kwargs ):
        
        cachePath = "{0}/{1}".format( self.defaultCacheDirectory, self.defaultCacheName )
        
              
        #Return the path
        returnPath = checkInputs.checkBooleanKwargs( kwargs, False, 'path', 'cachePath', 'loc', 'location', 'cacheLocation', 'returnPath', 'returnLoc', 'returnLocation' )
        if returnPath == True:
            return cachePath
        
        #Open file and decode data
        try:
            textFile = open( cachePath, "r")
        except:
            return None
        try:
            outputData = self.decodeData( textFile.read(), decode = True )
        except:
            outputData = None
        textFile.close()
        
        
        #Delete the cache file
        validArgs = checkInputs.validKwargs( kwargs, 'c', 'clear', 'clean', 'clearCache', 'cleanCache', 'delCache', 'deleteCache' )
        for i in range( len( validArgs ) ):
            try:
                if kwargs[validArgs[i]] == True:
                    try:
                        os.remove( cachePath )
                        break
                    except:
                        pass
                #Only remove individual record instead
                elif type( kwargs[validArgs[i]] ) == str and outputData != None:
                    outputData.pop( kwargs[validArgs[i]], None )
            except:
                pass
        
        #Delete individual value
        if outputData != None:
            validArgs = checkInputs.validKwargs( kwargs, 'delValue', 'delKey', 'deleteValue', 'deleteKey', 'clearValue', 'clearKey', 'removeValue', 'removeKey' )
            deleteValue = None
            for i in range( len( validArgs ) ):
                outputData.pop( kwargs[validArgs[i]], None )
                
            #Write back to cache
            try:
                textFile = open( cachePath, "w")
                textFile.write( self.encodeData( outputData, encode = True ) )
                textFile.close()
            except:
                pass
            
            #Return single value
            validArgs = checkInputs.validKwargs( kwargs, 'k', 'v', 'key', 'value' )
            keyValue = None
            for i in range( len( validArgs ) ):
                try:
                    keyValue = outputData[kwargs[validArgs[i]]]
                    break
                except:
                    keyValue = None
                    
            if len( validArgs ) > 0:
                return keyValue
                
        #Print data
        printCache = checkInputs.checkBooleanKwargs( kwargs, False, 'p', 'display', 'printOutput', 'printCache', 'displayCache' )

        if self.printProgress == True and ( len( kwargs ) == 0 or printCache == True ):
            for imageHash in outputData.keys():
                print "Hash: {0}".format( imageHash )
                if len( outputData[imageHash][2] ) > 0:
                    print "   URL: {0}".format( outputData[imageHash][2] )
                print "   Best cutoff mode: {0}".format( outputData[imageHash][0] )
                for cutoffMode in outputData[imageHash][1].keys():
                    if len( outputData[imageHash][1][cutoffMode] ) > 0:
                        print "      Cutoff mode {0}:".format( cutoffMode )
                        for bitsPerPixel in outputData[imageHash][1][cutoffMode].keys():
                            print "         Storage with {0} bits per pixel: {1}".format( bitsPerPixel, outputData[imageHash][1][cutoffMode][bitsPerPixel]*bitsPerPixel )   
                print 
            
            
        #If the hash should be calculated
        validArgs = checkInputs.validKwargs( kwargs, 'h', 'hash', 'returnHash', 'calculateHash', 'imageHash', 'MD5', 'imageMD5' )
        returnHash = None
        for i in range( len( validArgs ) ):
            try:
                if kwargs[validArgs[i]] == True:
                    returnHash = self.imageName
                    break
                elif self.readImage( str( kwargs[validArgs[i]] ) ) != None:
                    returnHash = str( kwargs[validArgs[i]] )
                    break
                else:
                    raise ImageStoreError( "can't read image" )
            except:
                returnHash = None
            
        if returnHash != None:
        
            customImage = self.readImage( returnHash )
            
            if customImage == None:
                return None
            
            else:
        
                #Find md5 of image
                imageHash = md5.new()
                try:
                    imageHash.update( customImage.tostring() )
                except:
                    pass
                imageMD5 = imageHash.hexdigest()
                
                return imageMD5
            
            
        #Return the stored data
        return outputData
        
    def readImage( self, location ):
        
        location = str( location )
        
        #Load from URL
        if any( value in location for value in self.protocols ):
                        
            try:
                location = cStringIO.StringIO( urllib2.urlopen( location ).read() )
                
            except:
                return None
                
        #Open image
        try:
            return Image.open( location ).convert( "RGB" )
            
        except:
            return None

#Compress into zip file
class ImageStoreZip:
    
    zipName = "ImageInfo.zip"
        
    @classmethod
    def write( self, input, fileName, **kwargs ):
        
        #Reset if already exists
        resetZip = checkInputs.checkBooleanKwargs( kwargs, False, 'r', 'd', 'reset', 'delete', 'resetZip', 'deleteZip', 'resetFile', 'deleteFile', 'resetZipFile', 'deleteZipFile' )
        
        #Get location to store zip file
        path = ImageStore.defaultImageDirectory
            
        #Remove final slash
        path.replace( "\\", "/" )
        while path[-1] == "/":
            path = path[:-1]
        
        if ImageStore().validPath( path ) == False:
            return False
            
        else:
            zipLocation = "{0}/{1}".format( path, self.zipName )
            if resetZip == True:
                try:
                    os.remove( zipLocation )
                except:
                    pass
                    
            zip = zipfile.ZipFile( zipLocation, mode='a', compression=zipfile.ZIP_DEFLATED )
            
            try:
                zip.writestr( fileName, input )
            except:
                if ImageStore.printProgress == True:
                    print "Error: Failed to write zip file."
            zip.close()
    
    @classmethod
    def read( self, **kwargs ):
        
        #Get image location
        validArgs = checkInputs.validKwargs( kwargs, 'i', 'iL', 'iN', 'image', 'imageLoc', 'imageLocation', 'imageName' )
        imageLocation = None
        
        for i in range( len( validArgs ) ):
        
            try:
                imageLocation = kwargs[validArgs[i]]
                
                if ImageStore().validPath( imageLocation ) == True:
                    break
                else:
                    raise IOError( "image doesn't exist" )
                    
            except:
                imageLocation = None
                
        #Read if zip file
        if any( value in imageLocation for value in ImageStore.protocols ):
        
            imageLocation = cStringIO.StringIO( urllib2.urlopen( imageLocation ).read() )
            
            if zipfile.is_zipfile( imageLocation ) == True:
                zip = zipfile.ZipFile( imageLocation )
            else:
                zip = None
                
        elif zipfile.is_zipfile( imageLocation ) == True:
            zip = zipfile.ZipFile( imageLocation )
            
        else:
            zip = None
            
        #Read zip data
        if zip != None:
            nameList = zip.namelist()
                        
            if 'creationtime' in nameList:
            
                if 'version' in nameList:
                    versionNumber = zip.read( 'version' )
                    
                else:
                    versionNumber = "pre-2.0"
                    
                creation = zip.read( 'creationtime' )
                    
                if "@" in creation:
                    creationName = creation.split( "@" )[0]
                    creationTime = creation.split( "@" )[1]
                else:
                    creationName = None
                    creationTime = None
                    
            else:
                versionNumber = None
                creationName = None
                creationTime = None
                
            if 'url' in nameList:
                customURL = zip.read( 'url' )
            else:
                customURL = None
        
        else:
            versionNumber = "pre-2.0"
            creationName = None
            creationTime = None
            customURL = None
        
        return [versionNumber, creationTime, creationName, customURL, nameList]
    
    @classmethod
    def combine( self, **kwargs ):
        
        #Get location to read zip file
        path = "{0}/{1}".format( ImageStore.defaultImageDirectory, self.zipName )
            
        if ImageStore().validPath( path ) == False:
            return False
        
        #Get image location
        validArgs = checkInputs.validKwargs( kwargs, 'i', 'iL', 'iN', 'image', 'imageLoc', 'imageLocation', 'imageName' )
        imageLocation = None
        
        for i in range( len( validArgs ) ):
        
            try:
                imageLocation = kwargs[validArgs[i]]
                if ImageStore().validPath( imageLocation ) == True:
                    break
                else:
                    imageLocation = None
                    raise IOError( "image doesn't exist" )
                    
            except:
                imageLocation = None
        
        #Get zip location        
        validArgs = checkInputs.validKwargs( kwargs, 'z', 'zL', 'zN', 'zip', 'zipLoc', 'zipLocation', 'zipName' )
        zipLocation = path
        for i in range( len( validArgs ) ):
        
            try:
                zipLocation = kwargs[validArgs[i]]
                if ImageStore().validPath( zipLocation ) == True:
                    break
                else:
                    zipLocation = path
                    raise IOError( "zip file doesn't exist" )
                    
            except:
                zipLocation = path
        
        if imageLocation != None:
        
            locationOfImage = imageLocation.replace( "/", "\\\\" )
            locationOfZip = zipLocation.replace( "/", "\\\\" )
            
            #Copy zip file into picture
            call( 'copy /b "{0}" + "{1}" "{0}"'.format( locationOfImage, locationOfZip ), shell=True)
            
            os.remove( zipLocation )
            
            return True
            
        else:
            return False

class checkInputs:
    
    @classmethod
    def capitalLetterCombinations( self, *args ):
    
        returnList = []
        args = list( args )
        
        #Deal with spaces
        joinedArg = {}
        for arg in args:
            if " " in str( arg ):
                splitArg = str( arg ).split( " " )
                for i in range( len( splitArg ) ):
                    joinedArg[i] = self.capitalLetterCombinations( splitArg[i] )
        
        #Put together all combinations
        newArgs = ["".join( list( tupleValue ) ) for tupleValue in list( itertools.product( *[item for key, item in joinedArg.iteritems()] ) )]
        newArgs += [" ".join( list( tupleValue ) ) for tupleValue in list( itertools.product( *[item for key, item in joinedArg.iteritems()] ) )]
            
        #Check they don't exist
        for newArg in newArgs:
            if newArg not in args:
                args.append( newArg )
                
        #Find different upper and lower case combinations
        for arg in args :
            
            returnList.append( arg )
            
            if any( map( str.isupper, arg ) ):
            
                #If capital in text but not first letter
                if map( str.isupper, arg[0] )[0] == False:
                    returnList.append( ''.join( word[0].upper() + word[1:] for word in arg.split() ) )
                    returnList.append( arg.capitalize() )
                    
                #If capital is anywhere in the name as well as also first letter
                elif any( map( str.isupper, arg[1:] ) ):
                    returnList.append( arg.capitalize() )
                    
                returnList.append( arg.lower() )
                
            else:
            
                #If no capital letter is in at all
                returnList.append( ''.join( word[0].upper() + word[1:] for word in arg.split() ) )
        
        
        return sorted( set( filter( len, returnList ) ) )
    
    @classmethod
    def validKwargs( self, kwargs, *args ):
    
        valid = []
        
        for i in range( len( args ) ):
            newArgs = checkInputs.capitalLetterCombinations( args[i] )
            
            for value in newArgs:
            
                try:
                    kwargs[ value ]
                    if value not in valid:
                        valid.append( value )
                        
                except:
                    pass
                    
        return valid
   
    @classmethod     
    def checkBooleanKwargs( self, kwargs, default, *args ):
        
        opposite = not default
        validArgs = []
        
        for i in range( len( args ) ):
            validArgs += checkInputs.validKwargs( kwargs, args[i] )
        
        try:
            if kwargs[validArgs[0]] == opposite:
                return opposite
            else:
                return default
        except:
            return default

class RangeError( Exception ):
    pass
class ImageStoreError( Exception ):
    pass
