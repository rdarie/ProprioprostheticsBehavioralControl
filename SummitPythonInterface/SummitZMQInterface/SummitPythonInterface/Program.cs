﻿using System;
using System.Collections.Generic;
using System.Threading;
// Summit API DLLs
using Medtronic.SummitAPI.Classes;
using Medtronic.SummitAPI.Events;
using Medtronic.TelemetryM;
using Medtronic.NeuroStim.Olympus.Commands;
using Medtronic.NeuroStim.Olympus.DataTypes.PowerManagement;
using Medtronic.NeuroStim.Olympus.DataTypes.Therapy;
using Medtronic.NeuroStim.Olympus.DataTypes.DeviceManagement;
using Medtronic.NeuroStim.Olympus.DataTypes.Sensing;

using NetMQ;
using NetMQ.Sockets;

using Newtonsoft.Json;

namespace SummitPythonInterface
{
    class Program
    {
        // Defining SummitSystem to be static so it can be properly accessed by sensing event handlers
        static int qSize = 200;
        // Create a manager
        static SummitManager theSummitManager = new SummitManager("SummitTest", qSize);
        static bool theSummitManagerIsDisposed = false;
        static bool disableORCA = true;
        static SummitSystem theSummit;
        static SubscriberSocket stimSocket = new SubscriberSocket();
        
        static void Main(string[] args)
        {
            // Initialize the Summit Interface
            Console.WriteLine("Creating Summit Interface...");
            stimSocket.Connect("tcp://169.254.102.206:12345");
            stimSocket.SubscribeToAnyTopic();

            APIReturnInfo returnInfoBuffer;
            Console.CancelKeyPress += delegate
            {
                // call methods to clean up
                Console.WriteLine("Shutting down stim...");
                try
                {
                    // turn off sense
                    returnInfoBuffer = theSummit.WriteSensingEnableStreams(false, false, false, false, false, false, false, false);
                    theSummit.WriteSensingState(SenseStates.None, 0x00);
                    // turn off stim
                    theSummit.StimChangeTherapyOff(false);
                }
                catch
                {
                    Console.WriteLine("Shutting down stim Failed");
                    Console.WriteLine("Press any key to continue.");
                    Console.ReadKey();
                }
                finally
                {
                    // Dispose SummitManager, disposing all SummitSystem objects
                    if (!theSummitManagerIsDisposed)
                    {
                        theSummitManager.Dispose();
                        theSummitManagerIsDisposed = true;
                        stimSocket.Close();
                        stimSocket.Dispose();
                    }
                    Console.WriteLine("CLOSED by Ctrl-C");
                }
            };
            // Tell user this code is not for human use
            Console.WriteLine("Starting Summit Stimulation Adjustment Training Project");
            Console.WriteLine("Before running this training project, the RLP should be used to configure a device to have two groups - A and B - with at least one program defined.");
            Console.WriteLine("WARNING!  This code is not for human use.");
            // Console.ReadKey();
            Console.WriteLine("Proceeding");


            // Connect to the INS using a function based on the Summit Connect training code.
            theSummit = SummitConnect(theSummitManager);

            // Check if the connection attempt was successful
            if (theSummit == null)
            {
                Console.WriteLine("Failed to connect, disponsing and closing.");
                //Console.ReadKey();
                // Dispose SummitManager, disposing all SummitSystem objects
                theSummitManager.Dispose();
                return;
            }

            //check battery level and display
            BatteryStatusResult outputBuffer;
            APIReturnInfo commandInfo = theSummit.ReadBatteryLevel(out outputBuffer);

            TelemetryModuleInfo info;
            theSummit.ReadTelemetryModuleInfo(out info);

            Console.WriteLine();
            Console.WriteLine(String.Format("CTM Battery Level: {0}", info.BatteryLevel));

            // Ensure the command was successful before using the result
            if (commandInfo.RejectCode == 0)
            {
                string batteryLevel = outputBuffer.BatteryLevelPercent.ToString();
                Console.WriteLine("INS Battery Level: " + batteryLevel);
            }
            else
            {
                Console.WriteLine("Unable to read battery level");
            }
            Console.WriteLine();
            // Turn off sensing so we can config sensing
            returnInfoBuffer = theSummit.WriteSensingEnableStreams(false, false, false, false, false, false, false, false);
            theSummit.WriteSensingState(SenseStates.None, 0x00);

            // ******************* Create a sensing configuration for Time Domain channels *******************
            List<TimeDomainChannel> TimeDomainChannels = new List<TimeDomainChannel>(4);
            TdSampleRates the_sample_rate = TdSampleRates.Sample0500Hz;

            // First Channel Specific configuration: Channels 0 and 1 are Bore 0.
            // Sample rate must be consistent across all TD channels or disabled for individuals.
            // Channel differentially senses from contact 0 to contact 1
            // Evoked response mode disabled, standard operation
            // Low pass filter of 100Hz applied.
            // Second low pass filter also at 100Hz applied
            // High pass filter at 8.6Hz applied.
            TimeDomainChannels.Add(new TimeDomainChannel(
                the_sample_rate, /////////////////////////
                TdMuxInputs.Mux5,
                TdMuxInputs.Mux6,
                TdEvokedResponseEnable.Standard,
                TdLpfStage1.Lpf450Hz,
                TdLpfStage2.Lpf1700Hz,
                TdHpfs.Hpf0_85Hz));
            TimeDomainChannels.Add(new TimeDomainChannel(
                TdSampleRates.Disabled,
                TdMuxInputs.Mux1,
                TdMuxInputs.Mux4,
                TdEvokedResponseEnable.Standard,
                TdLpfStage1.Lpf450Hz,
                TdLpfStage2.Lpf1700Hz,
                TdHpfs.Hpf0_85Hz));
            TimeDomainChannels.Add(new TimeDomainChannel(
                the_sample_rate, ////////////////////////////
                TdMuxInputs.Mux1,
                TdMuxInputs.Mux4,
                TdEvokedResponseEnable.Standard,
                TdLpfStage1.Lpf450Hz,
                TdLpfStage2.Lpf1700Hz,
                TdHpfs.Hpf0_85Hz));
            TimeDomainChannels.Add(new TimeDomainChannel(
                TdSampleRates.Disabled,
                TdMuxInputs.Mux5,
                TdMuxInputs.Mux6,
                TdEvokedResponseEnable.Standard,
                TdLpfStage1.Lpf450Hz,
                TdLpfStage2.Lpf1700Hz,
                TdHpfs.Hpf0_85Hz));
            // ******************* Set up the FFT *******************
            // Create a 256-element FFT that triggers every half second. Use a Hann window and stream all of the bins (if FFT streaming is enabled in later command).
            FftConfiguration fftChannel = new FftConfiguration();
            fftChannel.Size = FftSizes.Size0256;
            fftChannel.Interval = 1000;
            fftChannel.WindowEnabled = true;
            fftChannel.WindowLoad = FftWindowAutoLoads.Hann100;
            fftChannel.StreamSizeBins = 0;
            fftChannel.StreamOffsetBins = 0;
            // ******************* Set up the Power channels *******************
            // Set up two power summation channels per time domain channel, use various bands for each.
            List<PowerChannel> powerChannels = new List<PowerChannel>();
            powerChannels.Add(new PowerChannel(10, 20, 30, 40));
            powerChannels.Add(new PowerChannel(11, 21, 31, 41));
            powerChannels.Add(new PowerChannel(12, 22, 32, 42));
            powerChannels.Add(new PowerChannel(13, 23, 33, 43));
            // Enable the calculation of the first band for every time domain channel.
            //BandEnables theBandEnables = BandEnables.Ch0Band0Enabled | BandEnables.Ch1Band0Enabled | BandEnables.Ch2Band0Enabled | BandEnables.Ch3Band0Enabled;
            BandEnables theBandEnables = 0;
            // ******************* Set up the miscellaneous settings *******************
            // Disable bridging functionality
            // Stream time domain data every 50ms.
            // Disable the loop recorder
            MiscellaneousSensing miscsettings = new MiscellaneousSensing();
            miscsettings.Bridging = BridgingConfig.None;
            miscsettings.StreamingRate = StreamingFrameRate.Frame50ms;
            miscsettings.LrTriggers = LoopRecordingTriggers.None;
            // ******************* Write the sensing configuration to the device *******************
            // Writing the sensing configuration must occur in a specific order.
            // Time domain channels must be configured before FFT, FFT must occur before power channels
            // If FFT or power channels are not being used they do not need to be configured
            // Miscellaneous settings need to be configured last (excluding accelerometer)
            // Accelerometer settings can be set at any time.
            Console.WriteLine("Writing sense configuration...");
            returnInfoBuffer = theSummit.WriteSensingTimeDomainChannels(TimeDomainChannels);
            Console.WriteLine("Write TD Config Status: " + returnInfoBuffer.Descriptor);
            returnInfoBuffer = theSummit.WriteSensingFftSettings(fftChannel);
            Console.WriteLine("Write FFT Config Status: " + returnInfoBuffer.Descriptor);
            returnInfoBuffer = theSummit.WriteSensingPowerChannels(theBandEnables, powerChannels);
            Console.WriteLine("Write Power Config Status: " + returnInfoBuffer.Descriptor);
            returnInfoBuffer = theSummit.WriteSensingMiscSettings(miscsettings);
            Console.WriteLine("Write Misc Config Status: " + returnInfoBuffer.Descriptor);
            returnInfoBuffer = theSummit.WriteSensingAccelSettings(AccelSampleRate.Sample64);
            Console.WriteLine("Write Accel Config Status: " + returnInfoBuffer.Descriptor);
            // ******************* Turn on LFP, turn off FFT, and Power Sensing Components *******************
            //returnInfoBuffer = theSummit.WriteSensingState(SenseStates.LfpSense | SenseStates.Fft | SenseStates.Power, 0x00);
            returnInfoBuffer = theSummit.WriteSensingState(SenseStates.LfpSense | 0 | 0, 0x00);
            Console.WriteLine("Write Sensing Config Status: " + returnInfoBuffer.Descriptor);
            // ******************* Register the data listeners *******************
            theSummit.DataReceivedTDHandler += theSummit_DataReceived_TD;
            // TODO: decide whether to keep these
            theSummit.DataReceivedPowerHandler += theSummit_DataReceived_Power;
            theSummit.DataReceivedFFTHandler += theSummit_DataReceived_FFT;
            //
            theSummit.DataReceivedAccelHandler += theSummit_DataReceived_Accel;
            // ******************* Start streaming *******************
            // Start streaming for time domain, FFT, power, accelerometer, and time-synchronization.
            // Leave streaming of detector events, adaptive stim, and markers disabled
            returnInfoBuffer = theSummit.WriteSensingEnableStreams(true, false, false, false, false, true, true, false);
            Console.WriteLine("Write Stream Config Status: " + returnInfoBuffer.Descriptor);
            // Create some standard buffers for the output values form the various inc/dec functions. 
            APIReturnInfo bufferInfo = new APIReturnInfo();

            // TODO: allow group changes
            double? currentFreq = 100;
            double?[] currentAmp = new double?[] {0, 0, 0, 0};
            int?[] currentPW = new int?[] {70, 70, 70, 70};
            byte[] programIndexes = new byte[] {0, 1, 2, 3};
            // Turn on therapy, if a POR reject is returned, attempt to reset it
            bufferInfo = theSummit.StimChangeTherapyOn();
            Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
            // Reset POR if set
            if (bufferInfo.RejectCodeType == typeof(MasterRejectCode)
                && (MasterRejectCode)bufferInfo.RejectCode == MasterRejectCode.ChangeTherapyPor)
            {
                // Inform user
                Console.WriteLine("POR set, resetting...");
                // Reset POR
                bufferInfo = resetPOR(theSummit);
                bufferInfo = theSummit.StimChangeTherapyOn();
            }
            if (bufferInfo.RejectCode != 0)
            {
                Console.WriteLine("Error during stim init, may not function properly. Error descriptor:" + bufferInfo.Descriptor);
            }
            // Read the stimulation settings from the device
            TherapyGroup insStateGroupA;
            bufferInfo = theSummit.ReadStimGroup(GroupNumber.Group0, out insStateGroupA);
            // Write out device 0 and 1 slot 0 local and INS state
            Console.WriteLine("");
            for (int i = 0; i < 4; i++)
            {
                Console.WriteLine("Group A Prog 0 INS State: Amp = " + insStateGroupA.Programs[i].AmplitudeInMilliamps.ToString()
                    + ", PW = " + insStateGroupA.Programs[i].PulseWidthInMicroseconds.ToString());
            }
            Console.WriteLine("Group Rate = " + insStateGroupA.RateInHz.ToString());
            // Change active group to 0
            bufferInfo = theSummit.StimChangeActiveGroup(ActiveGroup.Group0);
            Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
            //Thread.CurrentThread.Join(500);
            Thread.Sleep(500);
            int waitPeriod = 20; // wait this much after each command is sent
            int bToothDelay = 30; // add this much wait to account for transmission delay
            bool verbose = false;
            TimeSpan? theAverageLatency = TimeSpan.FromMilliseconds(0);
            bool recalcLatency = true;
            try
            {
                for (int i = 0; i < 4; i++)
                {
                    // Set amplitudes to 0
                    bufferInfo = theSummit.StimChangeStepAmp(programIndexes[i], -insStateGroupA.Programs[i].AmplitudeInMilliamps, out currentAmp[i]);
                    Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                    Thread.Sleep(waitPeriod);
                    // Set pw's to 70
                    Console.WriteLine(" Setting PWs to 70");
                    bufferInfo = theSummit.StimChangeStepPW(programIndexes[i], 70 - insStateGroupA.Programs[i].PulseWidthInMicroseconds, out currentPW[i]);
                    Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                    Console.WriteLine(" Wrote PW: " + currentPW[i].ToString());
                    Thread.Sleep(waitPeriod);
                }
                // Set the Stimulation Frequency to 100Hz, keep to sense friendly values
                //bufferInfo = theSummit.StimChangeStepFrequency(100 - insStateGroupA.RateInHz, true, out currentFreq);
                double freqDelta = 100 - insStateGroupA.RateInHz;
                if (freqDelta != 0)
                {
                    bufferInfo = theSummit.StimChangeStepFrequency(freqDelta, false, out currentFreq);
                    if (verbose) { Console.WriteLine(" Command Status:" + bufferInfo.Descriptor); }
                    Thread.Sleep(waitPeriod);
                }
                theSummit.StimChangeTherapyOff(false);
                // Tell user this code is not for human use
                Console.WriteLine("Starting Summit Connection Training Project");
                Console.WriteLine("This code is not for human use, either close program window or proceed by pressing a key");
                Console.ReadKey();
                Console.WriteLine("");
                // Turn on therapy, if a POR reject is returned, attempt to reset it
                bufferInfo = theSummit.StimChangeTherapyOn();
                Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                // Reset POR if set
                if (bufferInfo.RejectCodeType == typeof(MasterRejectCode)
                    && (MasterRejectCode)bufferInfo.RejectCode == MasterRejectCode.ChangeTherapyPor)
                {
                    // Inform user
                    Console.WriteLine("POR set, resetting...");
                    // Reset POR
                    bufferInfo = resetPOR(theSummit);
                    bufferInfo = theSummit.StimChangeTherapyOn();
                }
                if (bufferInfo.RejectCode != 0)
                {
                    Console.WriteLine("Error during stim init, may not function properly. Error descriptor:" + bufferInfo.Descriptor);
                }
                bool messageDots = false;
                string gotMessage;
                bool breakFlag = false;
                Console.WriteLine("ZMQ Starting to wait for a message.");
                while (!breakFlag)
                {

                    //listening for messages is blocking for 1000 ms, after which it will check if it should exit thread, and if not, listen again (have this so that this thread isn't infinitely blocking when trying to join)
                    stimSocket.TryReceiveFrameString(TimeSpan.FromMilliseconds(200), out gotMessage);

                    // string ack;

                    if (gotMessage == null) //no actual message received, just the timeout being hit
                    {

                        if (recalcLatency)
                        {
                            bufferInfo = theSummit.CalculateLatency(10, out theAverageLatency);
                            recalcLatency = false;
                            Console.WriteLine("Average Latency = " + theAverageLatency.ToString());
                        }
                        if (messageDots)
                        {
                            Console.Write("ZMQ  Waiting for a message   \r");
                            messageDots = false;
                        }
                        else
                        {
                            Console.Write("ZMQ  Waiting for a message...\r");
                            messageDots = true;
                        }

                        if (theSummitManagerIsDisposed)
                        {
                            break;
                        }
                        else
                        {
                            continue;
                        }
                    }
                    //recalcLatency = true;
                    StimParams stimParams = JsonConvert.DeserializeObject<StimParams>(gotMessage);
                    // Console.WriteLine("Received message: " + stimParams.ToString());
                    //
                    double newAmplitude = 0;
                    byte whichProgram = 0;
                    int index = 0;
                    for (int i = 0; i < 4; i++)
                    {
                        if (stimParams.Amplitude[i] > 0)
                        {
                            whichProgram = (byte)i;
                            newAmplitude = stimParams.Amplitude[i];
                            index = i;
                            break;
                        }
                    }
                    // Set the Stimulation Frequency, keep to sense friendly values
                    freqDelta = stimParams.Frequency - (double)currentFreq;
                    if (freqDelta != 0)
                    {
                        bufferInfo = theSummit.StimChangeStepFrequency(freqDelta, false, out currentFreq);
                        Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                        //Thread.CurrentThread.Join(waitPeriod);
                        Thread.Sleep(waitPeriod);
                        if (bufferInfo.RejectCode != 0)
                        {
                            Console.WriteLine("Error during stim, may not function properly. Error descriptor:" + bufferInfo.Descriptor);
                            // ack = "Exiting due to error";
                            // stimSocket.SendFrame(ack);
                            breakFlag = true;
                        }
                    }
                    if (breakFlag) { break; }
                    // Turn on Stim
                    //int adjustedWait = stimParams.DurationInMilliseconds - bToothDelay + (int)(1.5 * 1000 / currentFreq);
                    //int adjustedWait = stimParams.DurationInMilliseconds - bToothDelay;
                    TimeSpan aveLate = (TimeSpan)theAverageLatency;
                    int adjustedWait = stimParams.DurationInMilliseconds - bToothDelay - (int)aveLate.TotalMilliseconds + (int)(1 * 1000 / currentFreq);
                    if (adjustedWait < 0) { adjustedWait = 10; }
                    if (verbose) { Console.WriteLine("Adjusted wait time between trains is {0}", adjustedWait); }
                    double deltaAmp = newAmplitude - (double)currentAmp[index];
                    bufferInfo = theSummit.StimChangeStepAmp(whichProgram, deltaAmp, out currentAmp[index]);
                    Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                    Console.WriteLine("    Wrote Amplitude:" + currentAmp[index].ToString());
                    //Thread.CurrentThread.Join(waitPeriod);
                    Thread.Sleep(waitPeriod);
                    if (bufferInfo.RejectCode != 0)
                    {
                        Console.WriteLine("Error during stim, may not function properly. Error descriptor:" + bufferInfo.Descriptor);
                        breakFlag = true;
                    }
                    if (breakFlag) { break; }
                    // Let it run for the requested duration (subtract effect of having to wait for 2 pulses)
                    //Thread.CurrentThread.Join(adjustedWait);
                    Thread.Sleep(adjustedWait);
                    bufferInfo = theSummit.StimChangeStepAmp(whichProgram, -(double)currentAmp[index], out currentAmp[index]);
                    if (verbose)
                    {
                        Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                        Console.WriteLine("    Reverting Amplitude:" + currentAmp[index].ToString());
                    }
                    //Thread.CurrentThread.Join(waitPeriod);
                    Thread.Sleep(waitPeriod);
                    if (bufferInfo.RejectCode != 0)
                    {
                        Console.WriteLine("Error during stim, may not function properly. Error descriptor:" + bufferInfo.Descriptor);
                        breakFlag = true;
                    }
                    if (breakFlag) {break;}
                    if (stimParams.ForceQuit) {break;}
                }
            }
            finally
            {
                Console.WriteLine("");
                Console.WriteLine("Shutting down stim...");
                try
                {
                    // turn off sense
                    returnInfoBuffer = theSummit.WriteSensingEnableStreams(false, false, false, false, false, false, false, false);
                    theSummit.WriteSensingState(SenseStates.None, 0x00);
                    // turn off stim
                    for (int i = 0; i < 4; i++)
                    {
                        // Set amplitudes to 0
                        bufferInfo = theSummit.StimChangeStepAmp(programIndexes[i], -insStateGroupA.Programs[i].AmplitudeInMilliamps, out currentAmp[i]);
                        Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                        Thread.Sleep(waitPeriod);
                        // Set pw's to 70
                        bufferInfo = theSummit.StimChangeStepPW(programIndexes[i], 70 - insStateGroupA.Programs[i].PulseWidthInMicroseconds, out currentPW[i]);
                        Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                        Console.WriteLine(" Wrote PW :" + currentPW[i].ToString());
                        Thread.Sleep(waitPeriod);
                    }
                    theSummit.StimChangeTherapyOff(false);
                }
                catch {
                    Console.WriteLine("Shutting down stim Failed");
                    Console.WriteLine("Press any key to continue.");
                    Console.ReadKey();
                }
                // ***** Object Disposal
                Console.WriteLine("Stim stopped, disposing Summit");
                // Dispose SummitManager, disposing all SummitSystem objects
                if (!theSummitManagerIsDisposed)
                {
                    theSummitManager.Dispose();
                    theSummitManagerIsDisposed = true;
                    stimSocket.Dispose();
                }
                Console.WriteLine("Press any key to continue.");
                Console.ReadKey();
                Console.WriteLine("CLOSED");
            }
        }


        // Sensing data received event handlers
        private static void theSummit_DataReceived_TD(object sender, SensingEventTD TdSenseEvent)
        {
            // Announce to console that packet was received by handler
            //Console.WriteLine("TD Packet Received, Global SeqNum:" + TdSenseEvent.Header.GlobalSequence.ToString()
            //   + "; Time Generated:" + TdSenseEvent.GenerationTimeEstimate.Ticks.ToString() + "; Time Event Called:" + DateTime.Now.Ticks.ToString());

            // Log some information about the received packet out to file

            //theSummit.LogCustomEvent(TdSenseEvent.GenerationTimeEstimate, DateTime.Now, "TdPacketReceived", TdSenseEvent.Header.GlobalSequence.ToString());
        }

        private static void theSummit_DataReceived_FFT(object sender, SensingEventFFT FftSenseEvent)
        {
            // Announce to console that packet was received by handler
            //Console.WriteLine("FFT Packet Received, Global SeqNum:" + FftSenseEvent.Header.GlobalSequence.ToString()
            //    + "; Time Generated:" + FftSenseEvent.GenerationTimeEstimate.Ticks.ToString() + "; Time Event Called:" + DateTime.Now.Ticks.ToString());

            // Log some information about the received packet out to file
            // theSummit.LogCustomEvent(FftSenseEvent.GenerationTimeEstimate, DateTime.Now, "TdPacketReceived", FftSenseEvent.Header.GlobalSequence.ToString());
        }

        private static void theSummit_DataReceived_Power(object sender, SensingEventPower PowerSenseEvent)
        {
            // Announce to console that packet was received by handler
            //Console.WriteLine("Power Packet Received, Global SeqNum:" + PowerSenseEvent.Header.GlobalSequence.ToString()
            //    + "; Time Generated:" + PowerSenseEvent.GenerationTimeEstimate.Ticks.ToString() + "; Time Event Called:" + DateTime.Now.Ticks.ToString());

            // Log some information about the received packet out to file
            // theSummit.LogCustomEvent(PowerSenseEvent.GenerationTimeEstimate, DateTime.Now, "TdPacketReceived", PowerSenseEvent.Header.GlobalSequence.ToString());
        }

        private static void theSummit_DataReceived_Accel(object sender, SensingEventAccel AccelSenseEvent)
        {
            // Announce to console that packet was received by handler
            //Console.WriteLine("AccelPacket Received, Global SeqNum:" + AccelSenseEvent.Header.GlobalSequence.ToString()
            //    + "; Time Generated:" + AccelSenseEvent.GenerationTimeEstimate.Ticks.ToString() + "; Time Event Called:" + DateTime.Now.Ticks.ToString());

            // Log some information about the received packet out to file
            // theSummit.LogCustomEvent(AccelSenseEvent.GenerationTimeEstimate, DateTime.Now, "TdPacketReceived", AccelSenseEvent.Header.GlobalSequence.ToString());
        }

        /// <summary>
        /// Resets the INS Power-On-Reset flag, which gets set when the device unexpectedly restarts. Can happen on low battery or on error. See logs for details. 
        /// </summary>
        /// <param name="theSummit">SummitSystem object to reset the POR on</param>
        /// <returns>APIReturn info object that details the POR flag reset results</returns>
        static APIReturnInfo resetPOR(SummitSystem theSummit)
        {
            Console.WriteLine("POR was set, resetting...");

            // reset POR
            theSummit.ResetErrorFlags(Medtronic.NeuroStim.Olympus.DataTypes.Core.StatusBits.Por);

            // check battery
            BatteryStatusResult theStatus;
            theSummit.ReadBatteryLevel(out theStatus);

            // perform interrogate command and check if therapy is enabled.s
            GeneralInterrogateData interrogateBuffer;
            APIReturnInfo theInfo = theSummit.ReadGeneralInfo(out interrogateBuffer);
            if (interrogateBuffer.IsTherapyUnavailable)
            {
                Console.WriteLine("Therapy still unavailable after reset");
            }

            // Return the info to main
            return theInfo;
        }

        /// <summary>
        /// Training function that illustrates a method of connecting to the Summit System
        /// </summary>
        /// <param name="projectName">ORCA defined project name</param>
        /// <returns></returns>
        private static SummitSystem SummitConnect(SummitManager theSummitManager)
        {
            // Bond with any CTMs plugged in over USB
            Console.WriteLine("Checking USB for unbonded CTMs. Please make sure they are powered on.");
            theSummitManager.GetUsbTelemetry();

            // Retrieve a list of known and bonded telemetry
            List<InstrumentInfo> knownTelemetry = theSummitManager.GetKnownTelemetry();

            // Check if any CTMs are currently bonded, poll the USB if not so that the user can be prompted to plug in a CTM over USB
            if (knownTelemetry.Count == 0)
            {
                do
                {
                    // Inform user we will loop until a CTM is found on USBs
                    Console.WriteLine("No bonded CTMs found, please plug a CTM in via USB...");
                    Thread.Sleep(2000);

                    // Bond with any CTMs plugged in over USB
                    knownTelemetry = theSummitManager.GetUsbTelemetry();
                } while (knownTelemetry.Count == 0);
            }

            // Write out the known instruments
            Console.WriteLine("Bonded Instruments Found:");
            foreach (InstrumentInfo inst in knownTelemetry)
            {
                Console.WriteLine(inst.SerialNumber);
            }

            // Connect to the first CTM available, then try others if it fails
            SummitSystem tempSummit = null;
            InstrumentPhysicalLayers typeOfConnection = InstrumentPhysicalLayers.Any;

            for (int i = 0; i < theSummitManager.GetKnownTelemetry().Count; i++)
            {
                // Perform the connection
                ManagerConnectStatus connectReturn = theSummitManager.CreateSummit(out tempSummit,
                    theSummitManager.GetKnownTelemetry()[i], typeOfConnection, 3);

                // Write out the result
                Console.WriteLine("Create Summit Result: " + connectReturn.ToString());

                // Break if it failed successful
                if (connectReturn == ManagerConnectStatus.Success)
                {
                    break;
                }
            }

            // Make sure telemetry was connected to, if not fail
            if (tempSummit == null)
            {
                // inform user that CTM was not successfully connected to
                Console.WriteLine("Failed to connect to CTM...");
                return null;
            }
            else
            {
                // inform user that CTM was successfully connected to
                Console.WriteLine("CTM Connection Successful!");

                ConnectReturn theWarnings;
                APIReturnInfo connectReturn;
                DiscoveredDevice? rfDevice = null;
                Console.WriteLine("Attempting RF Connection to last connected INS");
                connectReturn = tempSummit.StartInsSession(rfDevice, out theWarnings, disableORCA);

                if (!theWarnings.HasFlag(ConnectReturn.InitializationError))
                {
                    // Write out the warnings if they exist
                    Console.WriteLine("Summit Initialization: INS connected, warnings: " + theWarnings.ToString());
                    return tempSummit;
                }
                else
                {
                    //Medtronic.TelemetryM.InstrumentReturnCode
                    if (typeOfConnection == InstrumentPhysicalLayers.Any) { Thread.CurrentThread.Join(20000); }
                    Console.WriteLine("StartInsSession: Reject Code: " + Convert.ToString(connectReturn.RejectCode, 2).PadLeft(8, '0'));
                    Console.WriteLine("StartInsSession: Reject CodeType: " + connectReturn.RejectCodeType.ToString());
                    Console.WriteLine("StartInsSession: Descriptor: " + connectReturn.Descriptor);
                    Console.WriteLine("StartInsSession: Warnings: " + theWarnings.ToString());
                }
                // Discovery INS with the connected CTM, loop until a device has been discovered
                List<DiscoveredDevice> discoveredDevices;
                do
                {
                    Console.WriteLine("RF Connect failed. Discovering devices... ");
                    tempSummit.OlympusDiscovery(out discoveredDevices);
                } while (discoveredDevices.Count == 0);

                // Report Discovery Results to User
                Console.WriteLine("Olympi found:");
                foreach (DiscoveredDevice ins in discoveredDevices)
                {
                    Console.WriteLine(ins);
                }

                // Connect to the INS with default parameters and ORCA annotations
                Console.WriteLine("Creating Summit Interface.");

                // We can disable ORCA annotations because this is a non-human use INS (see disclaimer)
                // Human-use INS devices ignore the OlympusConnect disableAnnotation flag and always enable annotations.
                // Connect to a device
                int i = 0;
                try
                {
                    do
                    {
                        connectReturn = tempSummit.StartInsSession(discoveredDevices[0], out theWarnings, disableORCA);
                        //Medtronic.TelemetryM.InstrumentReturnCode
                        i++;
                        if (theWarnings.HasFlag(ConnectReturn.InitializationError))
                        {
                            //Medtronic.TelemetryM.InstrumentReturnCode
                            if (typeOfConnection == InstrumentPhysicalLayers.Any) { Thread.CurrentThread.Join(20000); }
                            Console.WriteLine("StartInsSession: Reject Code: " + Convert.ToString(connectReturn.RejectCode, 2).PadLeft(8, '0'));
                            Console.WriteLine("StartInsSession: Reject CodeType: " + connectReturn.RejectCodeType.ToString());
                            Console.WriteLine("StartInsSession: Descriptor: " + connectReturn.Descriptor);
                            Console.WriteLine("StartInsSession: Warnings: " + theWarnings.ToString());
                        }
                    } while (theWarnings.HasFlag(ConnectReturn.InitializationError) & i < 10);

                    // Write out the number of times a StartInsSession was attempted with initialization errors
                    Console.WriteLine("Initialization Error Count: " + i.ToString());

                    // Write out the final result of the example
                    if (connectReturn.RejectCode != 0)
                    {
                        Console.WriteLine("Summit Initialization: INS failed to connect");
                        theSummitManager.DisposeSummit(tempSummit);
                        return null;
                    }
                    else
                    {
                        // Write out the warnings if they exist
                        Console.WriteLine("Summit Initialization: INS connected, warnings: " + theWarnings.ToString());
                        return tempSummit;
                    }
                }
                catch
                {
                    Console.WriteLine("Summit Initialization: INS failed to connect");
                    theSummitManager.DisposeSummit(tempSummit);
                    return null;
                }
            }
        }
    }
}