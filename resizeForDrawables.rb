#!/usr/bin/env ruby

require 'fileutils'

class ResizeToDrawables

	@@verbose = true

	def self.run(original_image, mdpi, width=true)
		sizes = {"mdpi" => mdpi,
				"hdpi" => (mdpi * 1.5).to_i,
				"xhdpi" => mdpi * 2,
				"xxhdpi" => mdpi * 3,
				"xxxhdpi" => mdpi * 4}

		original_image = File.absolute_path original_image
		parent = File.dirname(File.dirname(original_image))
		# puts parent
		base_name = File.basename original_image
		sizes.each do |n,v|
			out_p = File.join(parent, "drawable-#{n}")
			# puts out_p
			# binding.pry
			FileUtils.mkdir_p out_p
			out_f = File.join(out_p, base_name)
			side = width ? "Width" : "Height"
			cmd = "sips --resample#{side} #{v} #{original_image} --out #{out_f}"
			puts cmd if @@verbose
			`#{cmd}`
		end
	end
end

if __FILE__ == $0
	files = ARGV[1..-1]
	match = ARGV[0].match(/^(\d+)(h?)$/)
	if match
		isWidth = match[2] != 'h'
		size = match[1].to_i
		if size > 0
			files.each { |f| ResizeToDrawables.run(f, size, isWidth) }
			exit
		end
	end
	puts "Resizes images into drawable folders. Size is mdpi size."
	puts "resize width:  #{__FILE__} 10 file [file...]"
	puts "resize height: #{__FILE__} 10h file [file...]"
end