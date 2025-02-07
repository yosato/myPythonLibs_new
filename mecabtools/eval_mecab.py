import os, sys, copy, imp, math

sys.path.append('./../myPythonLibs')
#sys.path.append(os.path.join(os.getenv('HOME'),'myProjects','my'))
from pythonlib_ys import main as myModule
import mecabtools

imp.reload(myModule)
imp.reload(mecabtools)

Debug=0

class WdParse:
    def __init__(self,Line,SPos):
        Wd,Rest=Line.split('\t')
        self.word=Wd
        self.sequence=Wd
        self.startpos=SPos
        self.leninchar=len(self.word)
        self.endpos=SPos+self.leninchar
        Fts=Rest.split(',')
        self.pos=Fts[0]
        self.otherfeats=Fts[1:]
    
class AmbSols:
    def __init__(self,Sols):
        (WffP,Seq)=self.wff_check(Sols)
        if not WffP:
            sys.exit('invalid solution set')
        else:
            self.sequence=Seq
            self.leninchar=len(Seq)
            self.leninwd=len(Sols)
            self.solutions=Sols


    def wff_check(self,OrgSols):
        Bool=True; Fst=True; Sentl=False
        Sols=copy.deepcopy(OrgSols)
        while not Sentl:
            if Fst:
                Fst=False
            else:
                if PrvSeq!=''.join([Wd.word for Wd in Sol]):
                    Bool=False
                    break
            if Sols:
                Sol=Sols.pop(0)
                PrvSeq=''.join([Wd.word for Wd in Sol])
            else:
                Sentl=True
        return Bool,PrvSeq
   
def main0(ResFP,SolFP,Strict=True,NoAmb=False):
    if not mecabtools.files_corresponding_p(ResFP,SolFP,Strict=True):
        sys.exit('result and solutions do not seem aligned')

    ResSentsRaw=mecabtools.extract_sentences(ResFP)
    SolSentsRaw=mecabtools.extract_sentences(SolFP)

    CumScores=([0,0,0],[0,0,0],[0,0])
    #Cntr=0
    for Cntr,ResSentRaw in enumerate(ResSentsRaw):
        if Debug:
            print('Sent '+str(Cntr+1)+': '+''.join([Line.split('\t')[0] for Line in ResSentRaw]))
        SolSentRaw=SolSentsRaw.__next__()
        if Debug>=2:
            print(ResSentRaw)
            print(SolSentRaw)
        MkdSentSol=mecabtools.mark_sentlines(SolSentRaw,[7,9])
        #for SentPair in SentPairs:
        if all(MkdLine[1] for MkdLine in MkdSentSol):
            if not all(MkdLine[2]=='original' for MkdLine in MkdSentSol):
                SolSentRaw=[ MkdLine[1] for MkdLine in MkdSentSol ]
            #print(SolSentRaw)
                
            ResSent=process_chunk(ResSentRaw)
            SolSent=process_chunk(SolSentRaw,NoAmb)
            Scores=score_sent(ResSent,SolSent)
            if Debug:
                print(Scores)
            CumScores=cumulate_scores(CumScores,Scores)
            
    return calculate_fscore(CumScores)


def process_chunk(SolLines,NoAmb=False):

    def amb_miniloop(Lines, OrgPos):
        Ambs=[];CurNum=-1
        Line=Lines.pop(0)
        while Line!='====':
            if Line.startswith('@'):
                Pos=OrgPos
                CurNum+=1
                Ambs.append([])
            else:
                WdP=WdParse(Line,OrgPos)
                Ambs[CurNum].append(WdP)
                Pos=Pos+WdP.leninchar
                
            Line=Lines.pop(0)
        return Lines,AmbSols(Ambs),Pos

    Sentl=False
    Els=[]; Pos=0; Fst=True
    while not Sentl:
        if Fst:
            Fst=False
        else:
            if Line=='====':
                SolLines,Ambs,Pos=amb_miniloop(SolLines,Pos)
                if NoAmb:
                    Els.extend(Ambs.solutions[0])
                else:
                    Els.append(Ambs)
            else:
                WdP=WdParse(Line,Pos)
                Els.append(WdP)
                Pos=Pos+WdP.leninchar
           
        if not SolLines:
            Sentl=True
        else:
            Line=SolLines.pop(0)
    return Els

def process_sentsraw(SentsRaw):
    PSents=[]
    for SentRaw in SentsRaw:
        try:
            MkdLines=mecabtools.mark_sentlines(SentRaw,[7,9])
            if any(Line[1] is None for Line in MkdLines):
                pass
            else:
                ProcessedSent=process_chunk(SentRaw)
                PSents.append(ProcessedSent)
                #yield ProcessedSent
        except:
            process_chunk(SentRaw)
    return PSents
    

def calculate_fscore(Scores):
    Score,[RCnt,SCnt]=Scores
    L1Den=sum(Score)
    L2Den=Score[1]+Score[2]
    L3Den=Score[2]
    round5_pair=lambda Pair: (round(Pair[0],8),round(Pair[1],8),round((Pair[0]+Pair[1])/2,8))
    L1=round5_pair((L1Den/RCnt,L1Den/SCnt))
    L2=round5_pair((L2Den/RCnt,L2Den/SCnt))
    L3=round5_pair((L3Den/RCnt,L3Den/SCnt))
    return (('Level1',L1),('Level2',L2),('Level3',L3))


def score_sents(SentPairs):
    CumScores=([0,0,0],[0,0,0],[0,0]);Cntr=0
    for ResSent,SolSent in SentPairs:
        Cntr+=1
        if Debug>=2:  print('Sent '+str(Cntr))
        Scores=score_sent(ResSent,SolSent)
        CumScores=cumulate_scores(CumScores,Scores)
        if Debug>=2: print(CumScores)
    return CumScores

def score_sent(ResSent,SolSent):

    def score_sent_iter(ResSent,SolSent,CumScores):
        if isinstance(SolSent[0],AmbSols):
            Triple=handle_ambcase(SolSent,ResSent)
        else:
            if not aligned_ressol_p(ResSent[0],SolSent[0]):
                Triple=next_aligned(ResSent,SolSent)
            else:
                Triple=handle_simplecase(ResSent,SolSent)
        NResSents,NSolSents,Scores=Triple
        NScores=cumulate_scores(CumScores,Scores)
        return NResSents,NSolSents,NScores

    def handle_ambcase(OrgSolSent,OrgResSent):
        SolAmb=OrgSolSent[0]

        Score,ChosenReading=score_amb(SolAmb,OrgResSent)

        # you decide how many resunit to remove
        NewResSent,ConsumedResUnitCnt=closest_smaller(OrgResSent,SolAmb.leninchar)

        if not ChosenReading:
            SolCnt=len(SolAmb.solutions[0])
        else:
            SolCnt=len(ChosenReading)
        ElCnts=[ConsumedResUnitCnt,SolCnt]

        return NewResSent,OrgSolSent[1:],(Score,ElCnts)

    def handle_simplecase(ResSent,SolSent):
        Score=[0,0,0]
        SolEntry=SolSent.pop(0);ResEntry=ResSent.pop(0)
        Bit=compare_entries(ResEntry,SolEntry)
        Score[Bit-1]=Score[Bit-1]+1
        
        return ResSent,SolSent,(Score,[1,1])

    CumScores=([0,0,0],[0,0,0],[0,0])
    while ResSent and SolSent:
        if Debug>=2:
            print('Doing with result "'+ResSent[0].sequence+'" against solution "'+SolSent[0].sequence+'"')
        ResSent,SolSent,CumScores=score_sent_iter(ResSent,SolSent,CumScores)

            
    return CumScores


def compare_entries(E1,E2):
    if E1.startpos!=E1.startpos or E1.endpos!=E2.endpos:
        return 0
    else:
        WdP=E1.word==E2.word
        PosP=E1.pos==E2.pos
        OthersP=E1.otherfeats==E2.otherfeats
        if all([WdP,PosP,OthersP]):
            return 3
        elif WdP and PosP and not OthersP:
            return 2
        elif WdP and not PosP:
            return 1


def highest_scores(ScoresL):
    Prv=ScoresL[0]
    for Cur in ScoresL[1:]:
        Highest=higher_scores(Cur,Prv)
    return Highest


def relative_bitscore(Bits):
    Score=0
    for Cntr,Bit in enumerate(Bits):
        Score+=Bit*math.pow(2,Cntr)
    return Score

def bitwise_add(Iter1,Iter2):
    return [ Tup[0]+Tup[1] for Tup in zip(Iter1,Iter2) ]

def score_amb(SolAmb,ResSent):
    def score_reading(SolReading,ResSent):    
        # word level
        ScoreP=[0,0,0]
        for WdCntr,SolEntry in enumerate(SolReading):
            ResEntry=ResSent[WdCntr]
            Bit=compare_entries(ResEntry,SolEntry)
            if not Bit:
                break
            else:
                ScoreP[Bit-1]=ScoreP[Bit-1]+1

        return ScoreP

    HighestRelBScore=0;Highest=[0,0,0]
    ChosenReading=None
    # reading level
    for Reading in SolAmb.solutions:
        # score a reading, and compare
        Score=score_reading(Reading,ResSent)
        CurRelBScore=relative_bitscore(Score)
        if CurRelBScore>HighestRelBScore:
            Highest=Score
            HighestRelBScore=CurRelBScore
            ChosenReading=Reading

    return Highest,ChosenReading

def aligned_ressol_p(ResEl,SolEl):
    if isinstance(SolEl,AmbSols):
        for Seq in SolEl.values():
            for Wd in Seq:
                if Wd.startpos==ResEl.startpos:
                    return True
                else:
                    break
    elif SolEl.startpos==ResEl.startpos and SolEl.endpos==ResEl.endpos:
        return True
    return False

def sol_seqlen_inchar(SolDict):
    SolSeq0=SolDict[1]
    return sum([ len(SolWd[1]) for SolWd in SolSeq0 ])


def next_aligned(ResSent,SolSent):
        # the first element each is guaranteed to be different, so pop them
        SolSent.pop(0);SolRedCnt=1
        ResSent.pop(0);ResRedCnt=1
        # then we rely on the res position and word to find aligned equiv
        ResPosWds=[ (ResEl.startpos,ResEl.word) for ResEl in ResSent ]

        while SolSent:
            if isinstance(SolSent[0],AmbSols):
                break
            else:
                # then we try to see for each solel whether it has the equiv in res
                SolPosWd=SolSent[0].startpos,SolSent[0].word

                if SolPosWd in ResPosWds:
                    # and delete the bits up to there
                    ResRedCnt=ResRedCnt+ResPosWds.index(SolPosWd)
                    ResSent=ResSent[ResRedCnt-1:]
                    break
                else:
                    SolRedCnt+=1
                    SolSent.pop(0)
                    if SolSent and isinstance(SolSent[0],AmbSols):
                        break
            
        return ResSent,SolSent,([0,0,0],[ResRedCnt,SolRedCnt])
        
def closest_smaller(ResSent,SolLenInChars):
        CurResPos=ResSent[0].startpos
        GoalPos=CurResPos+SolLenInChars
        ResUnitCnt = 0
        #LstResUnit=len(ResSent)-1
        while True:
            if CurResPos>GoalPos:
                break
            else:
                ResUnitCnt+=1
                # this means you reach the end of res
                if ResUnitCnt==len(ResSent):
                    break
                CurResPos=ResSent[ResUnitCnt].startpos
            #if len(ResSent)>ResUnitCnt+1:
            #    CurEl=ResSent[ResUnitCnt]
            #    CurResPos=CurEl.startpos
            #else:
            #    break
        ResUnitCnt2Reduce=ResUnitCnt-1
        return ResSent[ResUnitCnt2Reduce:],ResUnitCnt2Reduce



#====

def cumulate_scores(Scores1,Scores2):
    PScores,ElCnts=zip(Scores1,Scores2)
    return (bitwise_add(PScores[0],PScores[1]),bitwise_add(ElCnts[0],ElCnts[1]))




def main():
    import argparse
    Parser=argparse.ArgumentParser()
    Parser.add_argument('-r','--results',required=True)
    Parser.add_argument('-s','--solutions',required=True)
    Parser.add_argument('--no-amb',action='store_true')
    Args=Parser.parse_args()

    if not all([ os.path.isfile(FP) for FP in (Args.results,Args.solutions) ]):
        sys.exit('one of the files not found')

    Scores=main0(Args.results,Args.solutions,NoAmb=Args.no_amb)
    
    print('\t'.join(['','Precision','Recall','\tFScore']))
    for Level,PRF in Scores:
        P=PRF[0];R=PRF[1];F=PRF[2]
        print('\t'.join([Level,str(P),str(R),str(F)]))
    
    

if __name__=='__main__':
    main()
