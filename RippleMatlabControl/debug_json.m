clear; clc;
jsonData = jsondecode(fileread('collated_proposals.json'));
jsonFreqs = zeros(size(jsonData, 1), 5);
jsonAmpls = zeros(size(jsonData, 1), 5);
%%
for rw = 1:size(jsonData, 1)
    for col = 0:4
        thisOne = jsonData(rw).(sprintf('proposal_%d', col));
        jsonFreqs(rw, col+1) = thisOne.ees.freq;
        jsonAmps(rw, col+1) = thisOne.ees.amp;
    end
end
writematrix(jsonFreqs, 'collated_proposals_freq.csv')
writematrix(jsonAmps, 'collated_proposals_amp.csv')

%%
jsonCheck = csvread('jsonCheck.csv');
achievedAmps = [];
achievedFreqs = [];
achievedElectrodes = [];
for rw = 1:size(jsonData, 1)
    proposedElectrode = jsonData(rw).proposed_electrode;
    for col = 1:5
       if jsonCheck(rw, col)
            achievedElectrodes = [achievedElectrodes; string(proposedElectrode)];
            achievedAmps = [achievedAmps; jsonAmps(rw, col)];
            achievedFreqs = [achievedFreqs; jsonFreqs(rw, col)];
       end
    end
end

writematrix([achievedAmps, achievedFreqs], 'achieved_params.csv');
achievedTable = table(achievedAmps, achievedFreqs, achievedElectrodes);
%% Setup the Import Options
opts = delimitedTextImportOptions("NumVariables", 4);

% Specify range and delimiter
opts.DataLines = [1, Inf];
opts.Delimiter = ",";

% Specify column names and types
opts.VariableNames = ["electrode", "amplitude", "freq", "reps"];
opts.VariableTypes = ["string", "double", "double", "double"];
opts = setvaropts(opts, 1, "EmptyFieldRule", "auto");
opts.ExtraColumnsRule = "ignore";
opts.EmptyLineRule = "read";

% Import the data
metaDataByTrial = readtable("C:\Users\Radu\Documents\GitHub\ProprioprostheticsBehavioralControl\RippleMatlabControl\metaDataByTrial_unique.csv", opts);


%% Clear temporary variables
clear opts

freqLink = zeros(size(achievedTable, 1), 1);
ampLink = zeros(size(achievedTable, 1), 1);
freqDifference = zeros(size(achievedTable, 1), 1);
ampDifference = zeros(size(achievedTable, 1), 1);
configIndices = [];
for idx = 1:size(achievedTable, 1)
    jsonElec = strcat("-", achievedTable.achievedElectrodes(idx));
    elecMatchMask = (metaDataByTrial.electrode == jsonElec);
    jsonAmp = achievedTable.achievedAmps(idx);
    ampMismatch = abs(metaDataByTrial{:, 'amplitude'}) - abs(jsonAmp);
    % should be positive, because we round down the abs()
    ampMismatch(ampMismatch > 0) = inf;
    ampMismatch(~elecMatchMask) = inf;
    ampMismatch = abs(ampMismatch);
    idxAmpMin = find(ampMismatch == min(ampMismatch));
    jsonFreq = achievedTable.achievedFreqs(idx);
    if jsonFreq < 3
       jsonFreq = 3;
    end
    freqMismatch = (metaDataByTrial{:, 'freq'} - jsonFreq);
    % should be positive
    freqMismatch(freqMismatch < 0) = inf;
    freqMismatch = abs(freqMismatch);
    freqMismatch(ampMismatch > min(ampMismatch)) = inf;
    idxFreqMin = find(freqMismatch == min(freqMismatch));
    %
    if size(idxAmpMin) == 1
        idxMin = idxAmpMin;
    else
        idxMin = intersect(idxFreqMin, idxAmpMin);
    end
    configIndices = [configIndices; idxMin];
    freqLink(idx) = metaDataByTrial{idxMin, 'freq'};
    ampLink(idx) = metaDataByTrial{idxMin, 'amplitude'};
    freqDifference(idx) = metaDataByTrial{idxMin, 'freq'} - jsonFreq;
    ampDifference(idx) = metaDataByTrial{idxMin, 'amplitude'} - jsonAmp;
end

outputMat = [achievedAmps, achievedFreqs, achievedElectrodes, ampLink, freqLink, ampDifference, freqDifference, configIndices];
writematrix(outputMat, 'alternative_achieved_params.csv');
nChosen = unique(configIndices);
disp(size(nChosen));