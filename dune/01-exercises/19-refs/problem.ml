open! Base

(* It is sometimes useful to create a single mutable value. We can do this
   using a ref. We can create an [int ref] containing 0 as follows:
*)
let x = ref 0

(* Then we can access the value in the ref using the ! operator, and
   we can update it using the := operator. So, we could increment our
   ref as follows:
*)
let () =
  x := !x + 1

(* Write a function min_and_max which returns a tuple containing the
   minimum and maximum values in a non-empty list of positive
   integers. Your function should raise if the list is empty.

   Your function should iterate over the list and maintain refs of the
   minimum and maximum values seen so far.  *)
let min_and_max lst =
  let min = ref Int.max_value in
  let max = ref 0 in
  let find_min_max x = 
    if x < !min
    then min := x;
    if x > !max
    then max := x in
  List.iter lst ~f:(find_min_max);
  (!min, !max)

  (*
  let calc_min int1 int2 =
    if int1 > int2
    then int2
    else int1 in
  let calc_max int1 int2 =
    if int1 < int2
    then int2
    else int1 in

  let min = List.fold lst ~init:Int.max_value ~f:(calc_min) in
  let max = List.fold lst ~init:0 ~f:(calc_max) in
  (min,max)
  *)
 
let%test "Testing min_and_max..." =
  [%compare.equal: int*int] (min_and_max [5;9;2;4;3]) (2,9) 
;;

let%test "Testing min_and_max..." =
  [%compare.equal: int*int] (min_and_max [11;15;7;34]) (7,34)
;;
