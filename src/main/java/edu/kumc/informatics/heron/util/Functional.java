/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.util;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

/**
 * see also fj and google collections
 * @author dconnolly
 */
public class Functional {
        public static <T> List<T> cons(T car, List<T> cdr) {
                LinkedList<T> out = new LinkedList<T>(cdr);
                out.addFirst(car);
                return out;
        }

        public static abstract class Function1<T, U> {
                public abstract U apply (T x);
        }

        public static <T, U> List<U> map(Function1<T, U> f, List<T> in) {
                List<U> out = new ArrayList<U>();
                for (T x : in) {
                        out.add(f.apply(x));
                }
                return out;
        }

        public static abstract class Predicate<T> {
                public abstract Boolean apply(T candidate);
        }

        public static <T> List<T> filter(List <T> candidates,
                Predicate<T> test) {
                ArrayList<T> out = new ArrayList<T>();
                for (T x: candidates) {
                        if (test.apply(x)) {
                                out.add(x);
                        }
                }
                return out;
        }

        public static <T> List<T> append(List<T> a, List<T> b) {
                List<T> out = new ArrayList(a);
                out.addAll(b);
                return out;
        }

        public static <T> String mkString(List <T> parts, String sep) {
                StringBuilder sb = new StringBuilder();
                Boolean first = true;
                for (T part: parts) {
                        if (first) {
                                first = false;
                        } else {
                                sb.append(sep);
                        }
                        sb.append(part);
                }
                return sb.toString();
        }

                /**
         * cribbed from http://stackoverflow.com/questions/521171/a-java-collection-of-value-pairs-tuples/521235#521235
         */
        public static class Pair<L,R> {

                private final L left;
                private final R right;

                public Pair(L left, R right) {
                        this.left = left;
                        this.right = right;
                }

                public L getLeft() {
                        return left;
                }
                public R getRight() {
                        return right;
                }

                @Override
                public int hashCode() {
                        return left.hashCode() ^ right.hashCode();
                }

                @Override
                public boolean equals(Object o) {
                        if (o == null) {
                                return false;
                        }
                        if (!(o instanceof Pair)) {
                                return false;
                        }
                        Pair pairo = (Pair) o;
                        return this.left.equals(pairo.getLeft())
                                &&
 this.right.equals(pairo.getRight());
                }
        }

}
