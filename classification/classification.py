from utils import *

class Classification(object):
    def __init__(self, 
                    use_algorithm,
                    path, 
                    pretrained_weights, 
                    batchsize, 
                    Iterations_Over_Dataset, 
                    data_gen_args, 
                    loss_function, 
                    num_classes, 
                    Image_size, 
                    calculate_uncertainty,
                    evaluation):

        self.use_algorithm = use_algorithm
        assert self.use_algorithm == "Classification"
        self.path = path
        self.pretrained_weights = pretrained_weights
        self.batchsize = batchsize
        self.Iterations_Over_Dataset = Iterations_Over_Dataset
        self.data_gen_args = data_gen_args
        self.loss_function = loss_function
        self.num_classes = num_classes
        self.Image_size = Image_size
        self.calculate_uncertainty = calculate_uncertainty
        self.evaluation = evaluation
    
    def data_prepration(self): 
        '''
        Get the number of input images and their shape
        If the last image dimension,. which should contain the channel information (1 or 3) is not existing e.g. for (512,512) add a 1 as the channel number.
        '''
        if self.Image_size == None:
            Training_Input_shape, num_channels, _ = get_input_image_sizes(self.path, self.use_algorithm)
        else:
            Training_Input_shape = self.Image_size
            num_channels = int(self.Image_size[-1])

        Folders = ["image", "image1", "image2", "image3", "image4", "image5", "image6", "image7"]

        number_input_images = len([element for element in os.listdir(self.path + "/train/") if element in Folders])
        network_input_size = np.array(Training_Input_shape)
        network_input_size[-1] = int(Training_Input_shape[-1]) * number_input_images
        network_input_size = tuple(network_input_size)
        logging.info("Number of input folders is: ", number_input_images)

        '''
        Import filenames and split them into train and validation set according to the variable -validation_split = 20%
        '''
        data_path = self.path + '/train'
        train_image_files, val_image_files = training_validation_data_split(data_path)

        steps_per_epoch = int(len(train_image_files)/self.batchsize)

        self.epochs = self.Iterations_Over_Dataset
        logging.info("Making:", steps_per_epoch, "steps per Epoch")
        return [Training_Input_shape, num_channels, network_input_size, 
                        data_path, train_image_files, val_image_files, steps_per_epoch]



    def data_generator(self, data_path, Training_Input_shape, num_channels, train_image_files):
        '''
        Prepare data in Training and Validation set 
        '''
        if not isinstance(self.num_classes, int):
            sys.exit("Number of classes has not been set. You net to set num_classes!")
        TrainingDataGenerator = training_data_generator_classification(Training_Input_shape,
                                                                           self.batchsize,
                                                                           num_channels,
                                                                           self.num_classes,
                                                                           train_image_files,
                                                                           self.data_gen_args,
                                                                           data_path,
                                                                           self.use_algorithm)

        ValidationDataGenerator = training_data_generator_classification(   Training_Input_shape,
                                                                            self.batchsize,
                                                                            num_channels,
                                                                            self.num_classes,
                                                                            train_image_files,
                                                                            self.data_gen_args,
                                                                            data_path,
                                                                            self.use_algorithm)
        return TrainingDataGenerator, ValidationDataGenerator
    
    def load_model(self, network_input_size):
        #################################################if self.use_algorithm == "Classification":
        '''
        Build the classificaiton model with a ResNet50 and initilize with pretrained, imagenet or random weights
        Initialize data generator 
        '''
        model = ResNet50(network_input_size,
                            Dropout = 0.1,
                             include_top=True,
                             weights=self.pretrained_weights,
                             input_tensor=None,
                             pooling='max',
                             classes=self.num_classes)
        if (self.pretrained_weights):
            model.load_weights(self.pretrained_weights, by_name=True, skip_mismatch=True)
        else:
            logging.info("No weigths given")
            #weights_path = get_imagenet_weights()
            #model.load_weights(weights_path, by_name=True, skip_mismatch=True)
        model.compile(loss=self.loss_function,
                          optimizer='Adam',
                          metrics=['accuracy'])

        logging.info(model.summary())
        return model

    def train_model(self, model,TrainingDataGenerator,ValidationDataGenerator , steps_per_epoch, val_image_files ):
        '''
        Set Model callbacks such as: 
        - Early stopping (after the validation loss has not improved for 25 epochs
        - Checkpoints: Save model after each epoch if the validation loss has improved 
        - Tensorboard: Monitor training live with tensorboard. Start tensorboard in terminal with: tensorboard --logdir=/path_to/logs 
        '''
        Early_Stopping = EarlyStopping(monitor='val_loss', patience=25, mode='auto', verbose=0)
        datasetname = self.path.rsplit("/",1)[1]
        checkpoint_filepath = (self.path + "/logs" + "/pretrained_weights_" + datasetname + ".hdf5") #.{epoch:02d}.hdf5")
        os.makedirs("./" + (self.path + "/logs"), exist_ok=True)
        model_checkpoint = ModelCheckpoint(checkpoint_filepath, monitor=('val_loss'), verbose=1, save_best_only=True)

        tensorboard = TensorBoard(log_dir="logs/" + self.path + "/" + format(time.time())) #, update_freq='batch')
        logging.info("Tensorboard log is created at: logs/  it can be opend using tensorboard --logdir=logs for a terminal in the InstantDL folder")

        #################################################if self.use_algorithm == "Classification":
        callbacks_list = [model_checkpoint, tensorboard, Early_Stopping]

        '''
        Train the model given the initialized model and the data from the data generator
        '''
        model.fit_generator(TrainingDataGenerator,
                                steps_per_epoch=steps_per_epoch,
                                validation_data=ValidationDataGenerator,
                                validation_steps=len(val_image_files),
                                max_queue_size=50,
                                epochs=self.epochs,
                                callbacks = callbacks_list,
                                use_multiprocessing=True)
        logging.info('finished Model.fit_generator')
        return model, checkpoint_filepath

    def test_set_evaluation(self, model, Training_Input_shape, num_channels):
        '''
        Get the names of the test images for model evaluation
        '''
        test_image_files = os.listdir(os.path.join(self.path + "/test/image"))
        num_test_img = int(len(os.listdir(self.path + "/test/image")))
        logging.info("Testing on", num_test_img, "test files")

        '''
        Initialize the testset generator
        '''
        testGene = testGenerator(Training_Input_shape, self.path, num_channels, test_image_files, self.use_algorithm)
        logging.info('finished testGene')
        results = model.predict_generator(testGene, steps=num_test_img, use_multiprocessing=False, verbose=1)
        logging.info("results", np.shape(results))
        logging.info('finished model.predict_generator')
        
        #################################################
        '''
        Save the models prediction on the testset by saving a .csv file containing filenames 
        and predicted classes to the results folder in the project path
        '''
        saveResult_classification(self.path, test_image_files, results)
        if self.evaluation == True:
            classification_evaluation(self.path)

        return results,test_image_files, num_test_img
        ################################################# if calculate_uncertainty == True:
    def uncertainty_prediction(self, results, checkpoint_filepath, network_input_size, Training_Input_shape, num_channels, test_image_files, num_test_img):    
        '''
        Uncertainty prediction for classification 
        Using: https://github.com/RobRomijnders/bayes_nn
        for uncertainty estimation with MC Dropout for classification
        '''
        if self.epochs > 0:
            uncertainty_weights = checkpoint_filepath
        else:
            uncertainty_weights = self.pretrained_weights
        model = ResNet50(   network_input_size,
                            Dropout = 0.5,
                            include_top=True,
                            weights=uncertainty_weights,
                            input_tensor=None,
                            pooling='max',
                            classes=self.num_classes)
        logging.info("Starting Uncertainty estimation")
        resultsMCD = []
        for i in range(0, 20):
            logging.info("Testing Uncertainty Number: ", str(i))
            testGene = testGenerator(Training_Input_shape, self.path, num_channels, test_image_files, self.use_algorithm)
            resultsMCD_pred = model.predict_generator(testGene,
                                                              steps=num_test_img,
                                                              use_multiprocessing=False,
                                                              verbose=1)
            resultsMCD.append(resultsMCD_pred)
        resultsMCD = np.array(resultsMCD)
        argmax_MC_Pred = (np.argmax(resultsMCD, axis=-1))
        average_MC_Pred = []
        for i in range(len(argmax_MC_Pred[1])):
            bincount = np.bincount(argmax_MC_Pred[:,i])
            average_MC_Pred.append(np.argmax(bincount))
        average_MC_Pred = np.array(average_MC_Pred)
        combined_certainty = np.mean(-1 * np.sum(resultsMCD * np.log(resultsMCD + 10e-6), axis=0), axis = 1)
        combined_certainty /= np.log(20) # normalize to values between 0 and 1
        saveResult_classification_uncertainty(  self.path,
                                                test_image_files,
                                                results,
                                                average_MC_Pred,
                                                combined_certainty)
        if self.evaluation == True:
            classification_evaluation(self.path)

    def run(self):    
        data_prepration_results = self.data_prepration()
        

        Training_Input_shape = data_prepration_results[0]
        num_channels = data_prepration_results[1]
        network_input_size = data_prepration_results[2]
        data_path = data_prepration_results[3]
        train_image_files = data_prepration_results[4]
        val_image_files = data_prepration_results[5]
        steps_per_epoch = data_prepration_results[6]

        TrainingDataGenerator, ValidationDataGenerator = self.data_generator(  data_path, 
                                                                                    Training_Input_shape, 
                                                                                    num_channels, 
                                                                                    train_image_files)

        model = self.load_model(network_input_size)
        model, checkpoint_filepath = self.train_model(  model,
                                                            TrainingDataGenerator,
                                                            ValidationDataGenerator , 
                                                            steps_per_epoch, 
                                                            val_image_files )

        results,test_image_files, num_test_img = self.test_set_evaluation(  model, 
                                                                                Training_Input_shape, 
                                                                                num_channels)

        self.uncertainty_prediction(    results, 
                                        checkpoint_filepath, 
                                        network_input_size, 
                                        Training_Input_shape, 
                                        num_channels, 
                                        test_image_files, 
                                        num_test_img)
        model = None
    