'''
Python BOX for OpenViBE 
Functionality: Perform Canonical Correlation Analysis (CCA) in Real-Time
Purpose: Classify 4-class SSVEP targets using CCA in real-time with OpenViBE and Python Box
	     Output the detected class label to a COM port - used for external application control
		 Umcomment to use this functionality for external application control

Aravind Ravi, October 2018
eBionics Lab
University of Waterloo
Email: aravind.ravi@uwaterloo.ca
'''

#import serial
import numpy
from sklearn.cross_decomposition import CCA

class MyOVBox(OVBox):
        
	def __init__(self):
		OVBox.__init__(self)
		self.signalHeader = None
		self.stimLabel = None
		self.stimCode = None
		self.frequencies = None
		self.samplingRate = None
		self.numTargs = None
		self.prevTime = 0
		
	def initialize(self):
	#Set the SSVEP flicker frequencies
		self.frequencies = self.setting['Frequencies']
		self.frequencies = (self.frequencies).split(",")
		self.frequencies = map(float,self.frequencies)
	#Set the sampling rate of the hardware	
		self.samplingRate = self.setting['Sampling Rate']
		self.samplingRate = float(self.samplingRate)
	#Set the number of SSVEP targets
		self.numTargs = self.setting['Number Of Targets']
	# we append to the box output a stimulation header. This is just a header, dates are 0.
		self.output[0].append(OVStimulationHeader(0., 0.))
		#self.ser = serial.Serial('COM34',9600)
	
	def process(self):
		def getReferenceSignals(length, target_freq):
		# generate sinusoidal reference templates for CCA for the first and second harmonics
			reference_signals = []
			t = numpy.arange(0, (length/(self.samplingRate)), step=1.0/(self.samplingRate))
			#First harmonics/Fundamental freqeuncy
			reference_signals.append(numpy.sin(numpy.pi*2*target_freq*t))
			reference_signals.append(numpy.cos(numpy.pi*2*target_freq*t))
			#Second harmonics
			reference_signals.append(numpy.sin(numpy.pi*4*target_freq*t))
			reference_signals.append(numpy.cos(numpy.pi*4*target_freq*t))
			reference_signals = numpy.array(reference_signals)
			return reference_signals
			
		def findCorr(n_components,numpyBuffer,freq):
		# Perform Canonical correlation analysis (CCA)
		# numpyBuffer - consists of the EEG
		# freq - set of sinusoidal reference templates corresponding to the flicker frequency
			cca = CCA(n_components)
			corr=numpy.zeros(n_components)
			result=numpy.zeros((freq.shape)[0])
			for freqIdx in range(0,(freq.shape)[0]):
				cca.fit(numpyBuffer.T,numpy.squeeze(freq[freqIdx,:,:]).T)
				O1_a,O1_b = cca.transform(numpyBuffer.T, numpy.squeeze(freq[freqIdx,:,:]).T)
				indVal=0
				for indVal in range(0,n_components):
					corr[indVal] = numpy.corrcoef(O1_a[:,indVal],O1_b[:,indVal])[0,1]
				result[freqIdx] = numpy.max(corr)
			return result
		             
                                
                
		for chunkIndex in range( (len(self.input[0])) ):
			if(type(self.input[0][chunkIndex]) == OVSignalHeader):
				self.signalHeader = self.input[0].pop()
		

			#Receives the data from OpenViBE	
			elif(type(self.input[0][chunkIndex]) == OVSignalBuffer):
				chunk = self.input[0].pop()
				numpyBuffer = numpy.array(chunk).reshape(tuple(self.signalHeader.dimensionSizes))
				#Generate a vector of sinusoidal reference templates for all SSVEP flicker frequencies
				freq1=getReferenceSignals(self.signalHeader.dimensionSizes[1],self.frequencies[0])
				freq2=getReferenceSignals(self.signalHeader.dimensionSizes[1],self.frequencies[1])
				freq3=getReferenceSignals(self.signalHeader.dimensionSizes[1],self.frequencies[2])
				freq4=getReferenceSignals(self.signalHeader.dimensionSizes[1],self.frequencies[3])
				#Application of the CCA python function for each of the frequencies
				n_components=1
				#Concatenate all templates into one matrix
				freq=numpy.array([freq1,freq2,freq3,freq4])
				#Compute CCA 
				result = findCorr(n_components,numpyBuffer,freq)
				#Find the maximum canonical correlation coefficient and corresponding class for the given SSVEP/EEG data
				max_result = max(result,key=float)
				predictedClass = numpy.argmax(result)+1
				#Print the predicted class label
				print(predictedClass)
				
				self.stimLabel = 'OVTK_StimulationId_Label_0'+str(predictedClass)
				self.stimCode = OpenViBE_stimulation[self.stimLabel]
				stimSet = OVStimulationSet(self.prevTime, self.getCurrentTime())
				self.prevTime = self.getCurrentTime()
                # the date of the stimulation is simply the current openvibe time when calling the box process
				stimSet.append(OVStimulation(self.stimCode, self.getCurrentTime(), 0.))
				#print(self.stimLabel) #DEBUG
				#print(self.frequencies) #DEBUG
				self.output[0].append(stimSet)
				'''
				if predictedClass==1:
					self.ser.write('1')
					
				elif predictedClass==2:
					self.ser.write('2')
					
				elif predictedClass==3:
					self.ser.write('3')
					
				elif predictedClass==4:
					self.ser.write('4')
				'''
		def uninitialize(self):
			end = self.getCurrentTime()
			self.output[0].append(OVStimulationEnd(end, end))
			print('Stopped Scenario');                            
                                
box = MyOVBox()
