Hi!

Nice to see you.

You have found Paperboy. A Python Script for the Waveshare 13.3" Spectra 6 ePaper display running on the Raspberry Pi. 

please set up the SPI Interface for the RasPi HAT according to the Waveshare wiki. 

Pyton requirements required: 
 - PIL
 - FLASK

The Python script is currently expecting ro be installed in 
/usr/local/bin/paperboy

please copy all files there. Or git clone directly into /usr/local/bin.

You can upload the folowing file types BMP, PNG, JPG and jpeg
The images you upload are automatically resized and cropped to the required ePaper size.

Since the panel is portrait native, expecting the connection facing down, landscape images are automatically rotated
so they are displayed correctly. The orientation of your frame can be set as "left" or "right" in the "orientation" file.

The Image is then dithered with the RGBY-BW palette and if you have the "Spectra 6 device palette" Option enabled then 
the palette is converted to a false color palette to enhance image quality. (I never use the default palette. ;) )

You can click the thumbnail to preview the dithered image. Don't worry they are supposed to look ugly. =)

I Think You'll figure out what the "Show image" and "delete" button is doing yourself. ^.^

There is also a handy category system where you can sort your images and a vault Option to hide selected categories if you are not loged in. 
The default password is "topsecret" *ba da dum...* you can currently change that in the "secret" file in your papaerboy folder.
Use your favorite text editor.

I'll probably write a change password option some times. Who knows. =)

Have fun playing around. I hope you like paperboy


Ah yes... The "Clear Display" and "Shutdown Raspberry Pi" buttons do what they say. 
Clear display makes the display go whitey and Shutdown... makes the Pi go sleepy. 
