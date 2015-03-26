# problem with the following: if ssh to TGEN fails, script continues execution. TODO: fix

set +e

for i in `seq 1 $1`;
do
  ( $TGEN "timeout $TIME weighttp -n 1000000 -c $i -t $i -k -H \"User-agent: mirage\" $A/index.html" & )
  timeout $TIME weighttp -n 1000000 -c $i -t $i -k -H "User-agent: mirage" $A/index.html
  python ./read_metrics.py "http://"$XS1 root $PASSWORD $TIME 5
  if [ ! -z "$C" ]; then
      python ./read_metrics.py "http://"$XS2 root $PASSWORD $TIME 5
  fi
done

set -e
