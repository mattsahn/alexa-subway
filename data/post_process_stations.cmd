perl -i -pe 's/ st$/ street/g' stations.txt 
perl -i -pe 's/ st / street /g' stations.txt 
perl -i -pe 's/ pkwy/ parkway/g' stations.txt 
perl -i -pe 's/ hts/ heights/g' stations.txt 
perl -i -pe 's/ sq^/ square/g' stations.txt 
perl -i -pe 's/ sq / square /g' stations.txt 
perl -i -pe 's/ sq$/ square/g' stations.txt 
perl -i -pe 's/ rd$/ road/g' stations.txt 
perl -i -pe 's/ ave$/ avenue/g' stations.txt 
perl -i -pe 's/ ave / avenue /g' stations.txt 
perl -i -pe 's/ av$/ avenue/g' stations.txt 
perl -i -pe 's/ av / avenue /g' stations.txt 
perl -i -pe 's/ ctr$/ center/g' stations.txt 
perl -i -pe 's/ ctr / center /g' stations.txt 
perl -i -pe 's/ pl$/ place/g' stations.txt 
perl -i -pe 's/ jct/ junction/g' stations.txt 
perl -i -pe 's/ blvd/ boulevard/g' stations.txt 
perl -i -pe 's/ av\// avenue /g' stations.txt
perl -i -pe 's/\|w /\|west /g' stations.txt
perl -i -pe 's/ hwy/ highway/g' stations.txt
perl -i -pe 's/\|e /\|east /g' stations.txt
perl -i -pe 's/\|s /\|south /g' stations.txt
perl -i -pe 's/\|n /\|north /g' stations.txt