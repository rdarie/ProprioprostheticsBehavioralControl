﻿using System;
using System.Threading;
using System.Collections.Generic;
using Medtronic.SummitAPI.Classes;
using Medtronic.TelemetryM;
using Medtronic.NeuroStim.Olympus.Commands;
using Medtronic.NeuroStim.Olympus.DataTypes.PowerManagement;
using Medtronic.NeuroStim.Olympus.DataTypes.Therapy;
using Medtronic.NeuroStim.Olympus.DataTypes.DeviceManagement;

namespace SummitStimulation
{
    class Program
    {
        static bool disableORCA = true;
        static void Main(string[] args)
        {
            // Tell user this code is not for human use
            Console.WriteLine("Starting Summit Stimulation Adjustment Training Project");
            Console.WriteLine("Before running this training project, the RLP should be used to configure a device to have two groups - A and B - with at least one program defined.");
            Console.WriteLine("This code is not for human use, either close program window or proceed by pressing a key");
            //Console.ReadKey();
            Console.WriteLine("");
            // Initialize the Summit Interface
            Console.WriteLine("Creating Summit Interface...");
            // Create a manager
            SummitManager theSummitManager = new SummitManager("SummitTest", verboseTraceLogging: true);
            // Connect to the INS using a function based on the Summit Connect training code.
            SummitSystem theSummit = SummitConnect(theSummitManager);
            // Check if the connection attempt was successful
            if (theSummit == null)
            {
                Console.WriteLine("Failed to connect, press a key to close program.");
                Console.ReadKey();

                // Dispose SummitManager, disposing all SummitSystem objects
                theSummitManager.Dispose();
                return;
            }
            // ***** Loop to read keyboard inputs
            printCommandList();
            ConsoleKeyInfo thekey = Console.ReadKey();
            // Create some standard buffers for the output values form the various inc/dec functions.
            APIReturnInfo bufferInfo = new APIReturnInfo();
            TherapyGroup insStateGroupA = new TherapyGroup();
            TherapyGroup insStateGroupB = new TherapyGroup();
            TherapyProgram stimProgramA = new TherapyProgram();
            List<APIReturnInfo> progClearBufferInfo = new List<APIReturnInfo>();
            List<APIReturnInfo> progModBufferInfo = new List<APIReturnInfo>();
            // Loop functionality until the "q"uit character is entered
            while (thekey.KeyChar != 'q')
            {
                bool changedStimConfig = false;
                switch (thekey.KeyChar)
                {
                    case 'x':
                        // Modify program settings
                        // Turn off therapy
                        Console.WriteLine("Turning therapy off...");
                        bufferInfo = theSummit.StimChangeTherapyOff(false);
                        // Read the stimulation settings from the device
                        bufferInfo = theSummit.ReadStimGroup(GroupNumber.Group0, out insStateGroupA);
                        // Copy all parameters from the current group0.program0
                        for (byte changeProgramIndex = 0; changeProgramIndex < 4; changeProgramIndex++)
                        {
                            TherapyProgram currentProgram = insStateGroupA.Programs[changeProgramIndex];
                            Console.WriteLine("");
                            Console.WriteLine("INS current program:");
                            Console.WriteLine(currentProgram.ToString());
                            Console.WriteLine("");
                            stimProgramA.Clone(currentProgram);
                            for (int eIdx = 0; eIdx < 17; eIdx++)
                            {
                                switch (changeProgramIndex)
                                {
                                    case 0:
                                        switch (eIdx)
                                        {
                                            case 2:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Cathode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            case 16:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Anode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            default:
                                                stimProgramA.Electrodes[eIdx].IsOff = true;
                                                break;
                                        };
                                        break;
                                    case 1:
                                        switch (eIdx)
                                        {
                                            case 4:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Anode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            case 7:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Cathode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            default:
                                                stimProgramA.Electrodes[eIdx].IsOff = true;
                                                break;
                                        };
                                        break;
                                    case 2:
                                        switch (eIdx)
                                        {
                                            case 8:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Anode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            case 11:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Cathode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            default:
                                                stimProgramA.Electrodes[eIdx].IsOff = true;
                                                break;
                                        };
                                        break;
                                    case 3:
                                        switch (eIdx)
                                        {
                                            case 13:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Anode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            case 15:
                                                stimProgramA.Electrodes[eIdx].ElectrodeType = ElectrodeTypes.Cathode;
                                                stimProgramA.Electrodes[eIdx].IsOff = false;
                                                break;
                                            default:
                                                stimProgramA.Electrodes[eIdx].IsOff = true;
                                                break;
                                        };
                                        break;
                                    default:
                                        break;
                                }
                                stimProgramA.Electrodes[eIdx].Reserved1 = 0;
                                stimProgramA.Electrodes[eIdx].Value = 63;
                                Console.WriteLine(stimProgramA.Electrodes[eIdx].ToString());
                            }
                            Console.WriteLine("");
                            Console.WriteLine("Writing new program:");
                            Console.WriteLine(stimProgramA.ToString());
                            // clear existing program
                            progClearBufferInfo = theSummit.zAuthStimModifyClearProgram(
                                GroupNumber.Group0, changeProgramIndex);
                            // Write this program
                            progModBufferInfo = theSummit.zAuthStimWriteProgram(
                                GroupNumber.Group0, changeProgramIndex, stimProgramA);
                            changedStimConfig = true;
                            }
                        break;
                    case 'c':
                        // Query device for the active group.
                        GeneralInterrogateData insGeneralInfo;
                        bufferInfo = theSummit.ReadGeneralInfo(out insGeneralInfo);

                        Console.WriteLine("");
                        Console.WriteLine("Ins active group:" + insGeneralInfo.TherapyStatusData.ActiveGroup.ToString());
                        break;
                    case 'b':
                        // Read the stimulation settings from the device
                        bufferInfo = theSummit.ReadStimGroup(GroupNumber.Group0, out insStateGroupA);
                        bufferInfo = theSummit.ReadStimGroup(GroupNumber.Group1, out insStateGroupB);

                        // Write out device 0 and 1 slot 0 local and INS state
                        Console.WriteLine("");

                        Console.WriteLine("Group A INS State: Amp = " + insStateGroupA.Programs[0].AmplitudeInMilliamps.ToString()
                            + ", PW = " + insStateGroupA.Programs[0].PulseWidthInMicroseconds.ToString()
                            + ", Period = " + insStateGroupA.RatePeriod.ToString());

                        Console.WriteLine("Group B INS State: Amp = " + insStateGroupB.Programs[0].AmplitudeInMilliamps.ToString()
                            + ", PW = " + insStateGroupB.Programs[0].PulseWidthInMicroseconds.ToString()
                            + ", Period = " + insStateGroupB.RatePeriod.ToString());
                        break;

                    default:
                        // Something else was pressed, trigger a command print
                        Console.WriteLine("");
                        Console.Write(" Unrecognized command, ");
                        printCommandList();
                        // Loop will print out the previous command status, inform user
                        Console.Write(" Previous ");
                        break;
                }
                // Print out the command's status
                Console.WriteLine(" Command Status:" + bufferInfo.Descriptor);
                if (changedStimConfig)
                {
                    // Print out the command's status
                    Console.WriteLine("   ClearProgram Status:" + progClearBufferInfo[0].Descriptor);
                    Console.WriteLine("   ClearVersion Status:" + progClearBufferInfo[1].Descriptor);
                    // Print out the command's status
                    Console.WriteLine("   WriteSlotParameters Status:" + progModBufferInfo[0].Descriptor);
                    Console.WriteLine("   WriteVersionParameters Status:" + progModBufferInfo[1].Descriptor);
                    Console.WriteLine("   ReadStimGroup Status:" + progModBufferInfo[2].Descriptor);
                }
                // Ask for another key
                thekey = Console.ReadKey();
            }
            // ***** Object Disposal
            Console.WriteLine("");
            Console.WriteLine("Shutting down stim...");
            theSummit.StimChangeTherapyOff(false);
            Console.WriteLine("Stim stopped, press key to dispose Summit");
            Console.ReadKey();

            // Dispose SummitManager, disposing all SummitSystem objects
            theSummitManager.Dispose();
            Console.WriteLine("CLOSED");

            // ***** Prompt user for final keypress before closing down the program.
            Console.WriteLine("Press key to exit");
            Console.ReadKey();
        }

        /// <summary>
        /// static function which prints out the defined command list.
        /// </summary>
        static void printCommandList()
        {
            Console.WriteLine("Command List:");
            Console.WriteLine("x to modify program settings (zAuth)");
            Console.WriteLine("b to check active group program 0 values, c to check which group is active");
            Console.WriteLine("q quits loop");
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
