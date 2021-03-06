function [f,x,TemporalWidth,PeriodWidth,OmitWidth,Direction] = PeriodicFilter(Period,TemporalWidth,PeriodWidth,OmitWidth,Direction)
% function f = PeriodicFilter(Period,TemporalWidth,PeriodWidth,OmitWidth,Direction)

if nargin < 5 || isempty(Direction)
    Direction = 'both';
end
if ~any(strcmpi(Direction,{'past','future','both'}))
    error('Direction must be one of {past, future, both}')
end

if nargin < 4 || isempty(OmitWidth)
    OmitWidth = 0;
end
if OmitWidth < 0, error('OmitWidth must be nonnegative'), end

if nargin < 3 || isempty(PeriodWidth)
    PeriodWidth = Period/50;
end
if PeriodWidth > Period, error('PeriodWidth should be <= Period'), end

if nargin < 2 || isempty(TemporalWidth)
    TemporalWidth = OmitWidth;
    j = 0;
    while j < 50 && TemporalWidth < 10^6
        TemporalWidth = TemporalWidth + 1;
        j = j + (mod(TemporalWidth,Period) <= PeriodWidth || mod(TemporalWidth,Period) >= Period-PeriodWidth);
    end
end
if TemporalWidth <= OmitWidth, error('TemporalWidth must be greater than OmitWidth'); end

x = -TemporalWidth:TemporalWidth;
y = mod(x,Period);
f = double((y <= PeriodWidth | y >= Period-PeriodWidth) & abs(x) > OmitWidth);
if strcmpi(Direction,'past')
    f(x>=0)=0;
elseif strcmpi(Direction,'future')
    f(x<=0)=0;
end
f = -f / max(sum(f),eps(0));
f(x==0) = 1;


    