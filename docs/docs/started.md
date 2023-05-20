# **Quokka in Three Cartoons**

The fundamental concept in Quokka is a **stream of Polars DataFrames**, which we call a **DataStream**. A Polars DataFrame is basically a Pandas DataFrame, except that it's backed by [Apache Arrow](https://arrow.apache.org/) and supports fast compute with [Polars](https://github.com/pola-rs/polars). Readers familiar with Spark RDDs can interpret a DataStream as an RDD where data partitions are materialized in sequence. In contrast to Spark, partitions can be consumed as soon as they are generated. This facilitates pipeline parallelism between multiple data processing stages and makes Quokka really fast.

The user defines **input readers** that generate a DataStream from a dataset. For example, Quokka's cloud CSV reader generates a DataStream from an S3 bucket of CSV files. The user can also define **stateful operators** that operate on one or more DataStreams to produce one more DataStream. Finally a DataStream could be written to an **output sink**, which could be a distributed in-memory dataset that can be converted to Pandas or stable storage on disk or S3. 

![Quokka Stream](quokkas-stream.svg)

In this illustration, the bush produces a DataStream of leaves and the forest produces a DataStream of acorns. The brown quokka consumes those two streams and magically turns them into a stream of strawberries. The grey quokka takes in this stream of strawberries, slices them up and puts them in a salad bowl.

Unfortunately, people like us can't slice strawberries for a living and have to process tables of numbers. Quokka exposes useful primitives that allow you to filter, aggregate and join DataStreams, similar to what you can do in Polars or Spark. Please look at the [tutorials](simple.md) to learn more.

It would be a dismal world if there is only one quokka of each kind. Quokka supports parallelism for stateful operators with **channels**, which are parallel instantiations of a stateful operator to achieve data parallelism. Input sources can also have channels to parallelize the reading of a data source. For example, we can have two bushes and two forests, and four brown quokkas.

<p style="text-align:center;"><img src="../quokkas-channel.svg" width=800></p>

While the user can manually specify the number of channels they want for operators, in most cases it's automagically decided for you based on what you are doing, similar to Spark. Each channel in an input source or stateful operator can be scheduled independently to a machine in a cluster. Actors on the same machine talk to each other through memory while actors on different machines communicate through the network. An example scheduling of our quokkas:

<p style="text-align:center;"><img src="../quokkas-placement.svg" width=800></p>

The user shouldn't have to worry about this scheduling in most cases if using the DataStream API. However I couldn't resist making this cartoon, and it might be cool to know how Quokka works under the hood.

<p align = "center">
Image credits: some icons taken from flaticon.com.
</p>