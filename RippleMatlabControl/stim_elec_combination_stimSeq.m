function [stimCmd, stimElectrodes, achievedParams] = stim_elec_combination_stimSeq(...
    cathode_list, anode_list, Chans_paddle_to_ripple, randomizedParamList, stimStep)

% This function is randomizing combinations of stim parameters for a given
% combination of anode(s) and cathode(s), it returns a stimString that is
% further used to trigger the defined stimulation

verbose = true;

% Anode = anodic pulse first (current > 0)
% Cathode = cathodic pulse first (current < 0)

% Random param list = [Freq , Amp, TL, PD, PR]

% pulse frequency
reqFreq  = randomizedParamList(1);
if verbose
    fprintf('\n\n\nStim command builder summary\n')
    fprintf('Requested freq was %4.2f\n', reqFreq)
end
% pulse amplitude (first phase)
reqAmp = randomizedParamList(2);
if verbose
    fprintf('Requested amplitude was %4.2f\n', reqAmp)
end
% train length
reqTL = randomizedParamList(3);
% phase duration (first phase)
reqPD = randomizedParamList(4);
% phase ratio (second phase compared to first phase)
reqPR = randomizedParamList(5);
%% Stimulation Parameters [STIMSEQ VERSION]

% Stimulation parameters
% sprintf('Electrodes selected as cathodes are : %d  \n', cathode_list)
% sprintf('Electrodes selected as anodes are : %d  \n', anode_list)
cathode_ripple_idx = Chans_paddle_to_ripple(cathode_list);
anode_ripple_idx = Chans_paddle_to_ripple(anode_list);
cathode_list_ripple = reshape(cat(1, cathode_ripple_idx{:}), 1, []);
anode_list_ripple = reshape(cat(1, anode_ripple_idx{:}), 1, []);
% stimElectrodes must be the electrode number in terms of ripple system
% (i.e 5 on the paddle means 2 on the ripple -> provide 5 if you want 2)
% Chans_paddle_to_ripple(5) returns 2 which is the ripple index of the 5th paddle electrode !
 
% all the following parameters are the same as cathode & anode signal in a biphasic pulse are just opposites

% If current is > 1.5 mA, double the length of every vector of parameters
% as every channel will be doubled with 2nd C-bank

% Amplitude
% number of cathodes
nC             = length(cathode_list_ripple);
if verbose
    fprintf('%d cathodes\n', nC);
end
% number of anodes
nA             = length(anode_list_ripple);
if verbose
    fprintf('%d anodes\n', nC);
end
nTotalContacts = (nC + nA);
if verbose
    fprintf('%d total contacts in request\n', nC);
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% divide the requested amplitude evenly among the channels
if isempty(cathode_list_ripple) && isempty(anode_list_ripple)
    error('no stim requested')
elseif isempty(cathode_list_ripple)
    stimElectrodes       = anode_list_ripple;
    phaseAmplitude_steps = ones(1, nA) * floor(reqAmp / (stimStep * nA));
    polarity  = ones(1, nA);
elseif isempty(anode_list_ripple)
    stimElectrodes       = cathode_list_ripple;
    phaseAmplitude_steps = ones(1, nC) * floor(reqAmp / (stimStep * nC));
    polarity  = zeros(1, nC);
else
    stimElectrodes       = [cathode_list_ripple, anode_list_ripple];
    phaseAmplitude_steps = [...
        ones(1, nC) * floor(reqAmp / (stimStep * nC)),...
        ones(1, nA) * floor(reqAmp / (stimStep * nA))];
    % Current flows from 1st electrode to 2nd
    polarity  = [zeros(1, nC), ones(1, nA)];
end
if verbose
    fprintf('stimulating on Ripple channels:\n');
    disp(stimElectrodes);
    fprintf('# of steps per channel: \n');
    disp(phaseAmplitude_steps);
    fprintf('#polarity per channel: \n');
    disp(polarity);
end
% duplicate the shared parameters, one for each channel
frequency_Hz         = ones(1, nTotalContacts) * reqFreq;
trainLength_ms       = ones(1, nTotalContacts) * reqTL;
phaseDuration_ms     = ones(1, nTotalContacts) * reqPD;
phaseRatios          = ones(1, nTotalContacts) * reqPR;
electrodeDelay_ms    = zeros(1, nTotalContacts);
% Generate stimulation string
if max(phaseAmplitude_steps) * stimStep > 1500
    error('Request exceeds max current!')
end

totalASteps = 0;
totalCSteps = 0;

for k=1:length(stimElectrodes)
    cmd(k).elec     = stimElectrodes(k);
    cmd(k).period   = cast(floor(30e3 / frequency_Hz(k)), 'int64');
    nearestFreq = 30e3 / cast(cmd(k).period, 'double');
    if verbose
        fprintf('nearest available frequency is %4.2f Hz\n', nearestFreq)
    end
    cmd(k).repeats  = cast(ceil(trainLength_ms(k) * frequency_Hz(k) / 1000), 'int64');
    cmd(k).action   = 'immed';
    
    % Create the first phase (cathodic) for stimulation.  This has a
    % duration of 200 us (6 clock cycles at 30 kHz), an amplitude of
    % 10, and negative polarity.
    secondPhaseAmplitude = floor(phaseAmplitude_steps(k) / phaseRatios(k));
    firstPhaseAmplitude = phaseRatios(k) * secondPhaseAmplitude;
    if verbose
        fprintf('the ratio between phases is %d, making the second phase %d steps in amplitude (%4.2f uA)\n',...
            phaseRatios(k), secondPhaseAmplitude, secondPhaseAmplitude * stimStep)
        fprintf('the first phase %d steps in amplitude (%4.2f uA)\n',...
            firstPhaseAmplitude, firstPhaseAmplitude * stimStep)
    end
    phaseLength = round(30e3 * (phaseDuration_ms(k) / 1000));
    cmd(k).seq(1) = struct(...
        'length', phaseLength, 'ampl', firstPhaseAmplitude,...
        'pol', polarity(k), ...
        'fs', 0, 'enable', 1, 'delay', 0, 'ampSelect', 1);
    %     % Create the inter-phase interval.  This has a duration of 100 us
    %     % (3 clock cycles at 30 kHz).  The amplitude is zero.  The
    %     % stimulation amp is still used so that the stim markers send by
    %     % the NIP will properly contain this phase.
    %
    %     cmd(k).seq(2) = struct(...
    %         'length', 1, 'ampl', 0,...
    %         'pol', 0, 'fs', 0, ...
    %         'enable', 0, 'delay', 0, 'ampSelect', 1);
    %
    % Create the second, anodic phase.  This has a duration of 200 us
    % (6 cycles at 30 kHz), and amplitude of 10, and positive polarity.
    if polarity(k)
        invPolarity = 0;
        totalASteps = totalASteps + firstPhaseAmplitude;
    else
        invPolarity = 1;
        totalCSteps = totalCSteps + firstPhaseAmplitude;
    end
    cmd(k).seq(2) = struct(...
        'length', phaseRatios(k) * phaseLength, 'ampl', secondPhaseAmplitude,...
        'pol', invPolarity, ...
        'fs', 0, 'enable', 1, 'delay', 0, 'ampSelect', 1);
end

achievedParams = [nearestFreq, -1 * totalCSteps * stimStep];
if verbose
    fprintf('total achieved cathodic current is %d steps (%4.2f uA)\n',...
        totalCSteps, achievedParams(2))
    fprintf('total achieved anodic current is %d steps (%4.2f uA)\n',...
        totalASteps, totalASteps * stimStep)
end
stimCmd = cmd;
