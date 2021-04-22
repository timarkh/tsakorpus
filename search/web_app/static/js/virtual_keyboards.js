function url_exists(url, callback) {
  fetch(url, { method: 'head' })
  .then(function(status) {
    callback(status.ok)
  });
}

function initialize_keyboard(lang, wordNum) {
	keysJsonUrl = 'static/kioskboard-1.4.0/kioskboard-keys-' + lang + '.json';
	url_exists(keysJsonUrl, function(exists) {
  		if (exists) {
  			let curKeyboard = {};
  			curKeyboard = $.extend(true, curKeyboard, KioskBoard);
  			alert(JSON.stringify(curKeyboard));
			curKeyboard.Run('#wf' + wordNum, {
			  /*!
			  * Required
			  * Have to define an Array of Objects for the custom keys. Hint: Each object creates a row element (HTML) on the keyboard.
			  * e.g. [{"key":"value"}, {"key":"value"}] => [{"0":"A","1":"B","2":"C"}, {"0":"D","1":"E","2":"F"}]
			  */
			  keysArrayOfObjects: null,

			  /*!
			  * Required only if "keysArrayOfObjects" is "null".
			  * The path of the "kioskboard-keys-${langugage}.json" file must be set to the "keysJsonUrl" option. (XMLHttpRequest to getting the keys from JSON file.)
			  * e.g. '/Content/Plugins/KioskBoard/dist/kioskboard-keys-english.json'
			  */
			  keysJsonUrl: keysJsonUrl,

			  /*
			  * Optional: (Special Characters Object)* Can override default special characters object with the new/custom one.
			  * e.g. {"key":"value", "key":"value", ...} => {"0":"#", "1":"$", "2":"%", "3":"+", "4":"-", "5":"*"}
			  specialCharactersObject: null,
			  */

			  // Optional: (Other Options)

			  // Language Code (ISO 639-1) for custom keys (for language support) => e.g. "en" || "tr" || "es" || "de" || "fr" etc.
			  // language: 'en',

			  // The theme of keyboard => "light" || "dark" || "flat" || "material" || "oldschool"
			  theme: 'light',

			  // Uppercase or lowercase to start. Uppercase when "true"
			  capsLockActive: false,

			  // Allow or prevent real/physical keyboard usage. Prevented when "false"
			  allowRealKeyboard: true,

			  // CSS animations for opening or closing the keyboard
			  cssAnimations: true,

			  // CSS animations duration as millisecond
			  cssAnimationsDuration: 360,

			  // CSS animations style for opening or closing the keyboard => "slide" || "fade"
			  cssAnimationsStyle: 'slide',

			  // Allow or deny Spacebar on the keyboard. The keyboard is denied when "false"
			  keysAllowSpacebar: true,

			  // Text of the space key (spacebar). Without text => " "
			  keysSpacebarText: ' ',

			  // Font family of the keys
			  keysFontFamily: 'sans-serif',

			  // Font size of the keys
			  keysFontSize: '22px',

			  // Font weight of the keys
			  keysFontWeight: 'normal',

			  // Size of the icon keys
			  keysIconSize: '25px',

			  // v1.1.0 and the next versions
			  // Allow or prevent mobile keyboard usage. Prevented when "false"
			  allowMobileKeyboard: false,

			  // v1.3.0 and the next versions
			  // Scrolls the document to the top of the input/textarea element. The default value is "true" as before. Prevented when "false"
			  autoScroll: true,
			});
		}
	});
}

function initialize_keyboards() {
	// First, replace elements with their copies to clear KioskBoard
	// event handlers.
	$('.virtual-keyboard').each(function(index) {
		var new_element = this.cloneNode(true);
		this.parentNode.replaceChild(new_element, this);
	})
	// Then assign new keyboards.
	$('.tier_select').each(function (index) {
		var wordNum = $(this).attr('id').replace(/^.*[^0-9]/g, '');
		var curTier = $('#lang' + wordNum.toString() + ' option:selected').val();
		if (curTier in keyboardsByTier) {
			var kbLang = keyboardsByTier[curTier];
			initialize_keyboard(kbLang, wordNum);
		}
	});
}