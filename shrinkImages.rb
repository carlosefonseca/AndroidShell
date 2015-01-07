#!/usr/bin/env ruby

# Will take all files whose name starts with 6 and tries to shrink them inplace, if they contain PNG or JPG data.
#
# sips is run on the file to check the data type.
#
# If already JPG, jpegtran will try to shrink it a bit.
#
# If PNG and has alpha channel, pngcrush will try to remove the alpha channel.
# If the image contains transparent pixels, it will not be modified further.
# If the new image does not contain an alpha channel, sips will convert it to JPG and jpegtran will run.
# Only a smaller JPG version replaces the original PNG version.

require 'mkmf'

def jpg?(sips)
  sips[/format: jpeg/]
end

def png?(sips)
  sips[/format: png/]
end

def alpha?(sips)
  sips[/Alpha: yes/]
end

def executable_exists?(name)
  find_executable0 name
end

execs = {:pngcrush => 'brew install pngcrush',
         :sips => 'xcode-select --install',
         :jpegtran => 'Not sure how to install. Maybe xcode-select --install', }

should_exit = false
execs.each do |k, v|
  unless executable_exists? k.to_s
    puts "⚠️  #{k} not installed!\n   $ #{v}"
    should_exit = true
  end
end

exit(1) if should_exit

original_space = 0
new_space = 0

Dir['6*'].each do |file|
  original_space += File.size file
  printf '%30s  ', file
  sips = `sips -g hasAlpha -g format #{file}`

  if jpg? sips
    print 'JPG...'
    `jpegtran -copy none -optimize -perfect -outfile #{file} #{file}`
    puts "\b\b\b Optim."
    new_space += File.size file
    next

  elsif png? sips
    print '           PNG...'

    if alpha?(sips)
      `pngcrush -s -reduce #{file} #{file}-crushed && mv #{file}-crushed #{file}`
      sips2 = `sips -g hasAlpha #{file}`
      if alpha? sips2
        puts "\b\b\b has Transparent Pixels"
        new_space += File.size file
        next
      end
    end

    jpg_file = file+'.jpg'
    `sips -s format jpeg -s formatOptions high #{file} --out #{jpg_file} && jpegtran -copy none -optimize -perfect -outfile #{jpg_file} #{jpg_file}`
    if File.size(file) < File.size(jpg_file)
      #PNG Smaller
      FileUtils.rm jpg_file
      puts "\b\b\b -> PNG (smaller than JPG)"
    else
      FileUtils.mv jpg_file, file
      #JPG Smaller
      puts "\b\b\b -> JPG"
    end
    new_space += File.size file
  end
end

def size_to_s(size)
  kb = size / 1024.0
  mb = kb / 1024.0
  (mb.abs < 1) ? "#{kb.round(2)} KB" : "#{mb.round(2)} MB"
end

if new_space == original_space
  puts 'No change in used space.'
elsif new_space < original_space
  puts "Decreased used space from  #{size_to_s(original_space)} to #{size_to_s(new_space)} (#{size_to_s(new_space-original_space)}) (#{(1.0*new_space/original_space*100.0).round(1)}%)"
else
  puts "INCREASED!!?!?!?!?!?! used space from  #{size_to_s(original_space)} to #{size_to_s(new_space)} (#{size_to_s(new_space-original_space)})"
end