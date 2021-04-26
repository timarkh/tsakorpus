function url_exists(url, callback) {
  fetch(url, { method: 'head' })
  .then(function(status) {
    callback(status.ok)
  });
}

function initialize_keyboard(keysJsonUrl, textboxSelector) {
	let curKeyboard = new KioskBoard({
	  keysArrayOfObjects: null,
	  keysJsonUrl: keysJsonUrl,

	  // The theme of keyboard => "light" || "dark" || "flat" || "material" || "oldschool"
	  theme: 'light',

	  capsLockActive: false,
	  allowRealKeyboard: true,

	  // CSS animations for opening or closing the keyboard
	  cssAnimations: true,
	  cssAnimationsDuration: 360,

	  // CSS animations style for opening or closing the keyboard => "slide" || "fade"
	  cssAnimationsStyle: 'slide',

	  // Allow or deny Spacebar on the keyboard. The keyboard is denied when "false"
	  keysAllowSpacebar: true,

	  // Text of the space key (spacebar). Without text => " "
	  keysSpacebarText: ' ',
	  keysFontFamily: 'sans-serif',
	  keysFontSize: '22px',
	  keysFontWeight: 'normal',
	  keysIconSize: '25px',
	  allowMobileKeyboard: true,

	  // v1.3.0 and the next versions
	  // Scrolls the document to the top of the input/textarea element. The default value is "true" as before. Prevented when "false"
	  autoScroll: true,
	});
	curKeyboard.Run(textboxSelector);
}

function add_keyboard(kbLang, wordNum, inputMethod) {
	if (inputMethod.length > 0) {
		inputMethod = '__' + inputMethod;
	}
	let keysJsonUrl = 'static/keyboards/keyboard-' + kbLang + inputMethod + '.json';
	let textboxSelector = '';
	if (wordNum > 1) {
		textboxSelector = '#wsearch_' + wordNum + ' .virtual-keyboard';
	}
	else {
		// Language of the first word determines keyboard language for the full-text textbox
		textboxSelector = '#first_word .virtual-keyboard, #txt';
	}
	url_exists(keysJsonUrl, function(exists) {
  		if (exists) {
			initialize_keyboard(keysJsonUrl, textboxSelector);
		}
		else {
			// Try keyboard without input method specified
			keysJsonUrl = 'static/keyboards/keyboard-' + kbLang + '.json';
			url_exists(keysJsonUrl, function(exists) {
				if (exists) {
					initialize_keyboard(keysJsonUrl, textboxSelector);
				}
			});
		}
	});
}

function disable_keyboards() {
	// Replace elements with their copies to clear KioskBoard
	// event handlers.
	$('.virtual-keyboard').each(function(index) {
		let new_element = this.cloneNode(true);
		this.parentNode.replaceChild(new_element, this);
	});
	$(".search_input").unbind('keydown');
	$(".search_input").on("keydown", search_if_enter);
	assign_autocomplete();
}

function initialize_keyboards() {
	disable_keyboards();
	// If the keyboards are switched off, then we are done here
	if (!$('#enable_virtual_keyboard').hasClass('keyboards_on')) {
		return;
	}
	// Assign new keyboards
	let inputMethod = $('#input_method option:selected').val();
	if (inputMethod === undefined) {
		inputMethod = '';
	}
	$('.tier_select').each(function (index) {
		let wordNum = $(this).attr('id').replace(/^.*[^0-9]/g, '');
		let curTier = $('#lang' + wordNum.toString() + ' option:selected').val();
		if (curTier in keyboardsByTier) {
			let kbLang = keyboardsByTier[curTier];
			add_keyboard(kbLang, wordNum, inputMethod);
		}
	});
}